import logging
from django.db import transaction
from django.core.cache import cache
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from django.shortcuts import get_object_or_404
from ..models import Orcamentos, ItensOrcamento
from .serializers import OrcamentosSerializer
from Entidades.models import Entidades
from Licencas.models import Empresas
from Pedidos.models import PedidoVenda, Itenspedidovenda
from core.utils import get_licenca_db_config, calcular_subtotal_item_bruto, calcular_total_item_com_desconto
from core.mixins.vendedor_mixin import VendedorEntidadeMixin
from rest_framework.permissions import IsAuthenticated
from parametros_admin.utils_pedidos import obter_parametros_pedidos, atualizar_parametros_pedidos

logger = logging.getLogger('Orcamentos')

class OrcamentoViewSet(viewsets.ModelViewSet, VendedorEntidadeMixin):
    permission_classes = [IsAuthenticated]
    modulo_requerido = 'Pedidos'
    serializer_class = OrcamentosSerializer
    lookup_field = 'pedi_nume'
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['pedi_forn', 'pedi_nume']
    filterset_fields = ['pedi_empr', 'pedi_fili', 'pedi_nume', 'pedi_forn', 'pedi_data']

    def get_object(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        if 'empresa' in self.kwargs:
            empresa = self.kwargs['empresa']
            filial = self.kwargs['filial']
            numero = self.kwargs['numero']
        else:
            lookup_value = self.kwargs.get(self.lookup_field)
            empresa = self.request.query_params.get('empr') or self.request.query_params.get('pedi_empr')
            filial = self.request.query_params.get('fili') or self.request.query_params.get('pedi_fili')
            numero = lookup_value

        numero = self.kwargs.get('numero') or self.request.query_params.get('numero')
        empresa = self.kwargs.get('empresa') or self.request.query_params.get('empresa')
        filial = self.kwargs.get('filial') or self.request.query_params.get('filial')

        if not empresa:
            empresa = self.request.data.get('pedi_empr')
        if not filial:
            filial = self.request.data.get('pedi_fili')
        if not numero:
            numero = self.request.data.get('pedi_nume')

        logger.debug(f"[get_object] Parametros recebidos: Empresa={empresa}, Filial={filial}, Numero={numero}")

        if not all([empresa, filial, numero]):
            raise ValidationError("Parâmetros empresa, filial e número são obrigatórios")

        try:
            queryset = self.get_queryset().filter(
                pedi_empr=empresa,
                pedi_fili=filial,
                pedi_nume=numero
            )
            obj = queryset.first()
            if not obj:
                raise NotFound(f"Orçamento {numero} não encontrado para empresa {empresa}, filial {filial}")
            self.check_object_permissions(self.request, obj)
            return obj
        except Exception as e:
            logger.error(f"Erro ao buscar orçamento: {e}")
            raise NotFound("Orçamento não encontrado")

    def get_queryset(self):
        from datetime import datetime
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")
        queryset = Orcamentos.objects.using(banco).all()
        queryset = self.filter_por_vendedor(queryset, 'pedi_vend')
        cliente_nome = self.request.query_params.get('cliente_nome')
        numero_orcamento = self.request.query_params.get('pedi_nume')
        empresa_id = self.request.query_params.get('pedi_empr')
        filial_id = self.request.query_params.get('pedi_fili')
        tem_filtros_especificos = cliente_nome or numero_orcamento
        if not tem_filtros_especificos:
            ano_atual = datetime.now().year
            queryset = queryset.filter(pedi_data__year=ano_atual)
            logger.info(f"Aplicando filtro por ano atual: {ano_atual}")
        if empresa_id:
            queryset = queryset.filter(pedi_empr=empresa_id)
        if filial_id:
            queryset = queryset.filter(pedi_fili=filial_id)
        if numero_orcamento:
            try:
                numero = int(numero_orcamento)
                queryset = queryset.filter(pedi_nume=numero)
                logger.info(f"Buscando orçamento específico: {numero} (sem filtro de ano)")
            except ValueError:
                return queryset.none()
        if cliente_nome:
            logger.info(f"Buscando por nome do cliente: {cliente_nome} (sem filtro de ano)")
            cache_key = f"entidades_cliente_{cliente_nome}_{empresa_id}"
            entidades_ids = cache.get(cache_key)
            if entidades_ids is None:
                entidades_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=cliente_nome)
                    .filter(enti_empr=empresa_id if empresa_id else None)
                    .values_list('enti_clie', flat=True)[:100]
                )
                cache.set(cache_key, entidades_ids, 300)
            if entidades_ids:
                queryset = queryset.filter(pedi_forn__in=entidades_ids)
            else:
                return queryset.none()
        return queryset.order_by('-pedi_nume')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            banco = get_licenca_db_config(request)
            page = self.paginate_queryset(queryset)
            if page is not None:
                empresas_cache = {}
                entidades_cache = {}
                empresas_ids = set(obj.pedi_empr for obj in page)
                empresas = Empresas.objects.using(banco).filter(empr_codi__in=empresas_ids)
                for empresa in empresas:
                    empresas_cache[empresa.empr_codi] = empresa.empr_nome
                entidades_keys = set((obj.pedi_forn, obj.pedi_empr) for obj in page)
                entidades = Entidades.objects.using(banco).filter(
                    enti_clie__in=[forn for forn, empr in entidades_keys],
                    enti_empr__in=[empr for forn, empr in entidades_keys]
                )
                for entidade in entidades:
                    cache_key = f"{entidade.enti_clie}_{entidade.enti_empr}"
                    entidades_cache[cache_key] = entidade.enti_nome
                context = self.get_serializer_context()
                context['empresas_cache'] = empresas_cache
                context['entidades_cache'] = entidades_cache
                serializer = self.get_serializer(page, many=True, context=context)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"[OrcamentoViewSet.list] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except ValidationError as e:
            logger.warning(f"[OrcamentoViewSet.create] Erro de validação: {e.detail}")
            return Response({'errors': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"[OrcamentoViewSet.create] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"[OrcamentoViewSet.retrieve] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        logger.debug(f"[OrcamentoViewSet.update] Dados da requisição: {request.data}")
        logger.debug(f"[OrcamentoViewSet.update] Args: {args}")
        logger.debug(f"[OrcamentoViewSet.update] Kwargs: {kwargs}")
        try:
            return super().update(request, *args, **kwargs)
        except ValidationError as e:
            logger.warning(f"[OrcamentoViewSet.update] Erro de validação: {e.detail}")
            return Response({'errors': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"[OrcamentoViewSet.update] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        try:
            orcamento = self.get_object()
            banco = get_licenca_db_config(self.request)
            if not banco:
                logger.error("Banco de dados não encontrado.")
                raise NotFound("Banco de dados não encontrado.")
            with transaction.atomic(using=banco):
                itens_count = ItensOrcamento.objects.using(banco).filter(
                    iped_empr=orcamento.pedi_empr,
                    iped_fili=orcamento.pedi_fili,
                    iped_pedi=str(orcamento.pedi_nume)
                ).count()
                if itens_count > 0:
                    ItensOrcamento.objects.using(banco).filter(
                        iped_empr=orcamento.pedi_empr,
                        iped_fili=orcamento.pedi_fili,
                        iped_pedi=str(orcamento.pedi_nume)
                    ).delete()
                    logger.info(f"Excluídos {itens_count} itens do orçamento {orcamento.pedi_nume}")
                orcamento.delete()
                logger.info(f"🗑️ Exclusão Orçamento ID {orcamento.pedi_nume} concluída")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"[OrcamentoViewSet.destroy] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='transformar-em-pedido')
    def transformar_em_pedido(self, request, slug=None, *args, **kwargs):
        try:
            orcamento = self.get_object()
            logger.debug(f"[transformar_em_pedido] Orçamento: {orcamento}")
            banco = get_licenca_db_config(request)
            if not banco:
                return Response({'erro': 'Banco de dados não encontrado'}, status=status.HTTP_404_NOT_FOUND)
            with transaction.atomic(using=banco):
                ultimo_pedido = PedidoVenda.objects.using(banco).filter(
                    pedi_empr=orcamento.pedi_empr,
                    pedi_fili=orcamento.pedi_fili
                ).order_by('-pedi_nume').first()
                proximo_numero = (ultimo_pedido.pedi_nume + 1) if ultimo_pedido else 1
                while PedidoVenda.objects.using(banco).filter(pedi_nume=proximo_numero).exists():
                    proximo_numero += 1
                pedido = PedidoVenda.objects.using(banco).create(
                    pedi_empr=orcamento.pedi_empr,
                    pedi_fili=orcamento.pedi_fili,
                    pedi_nume=proximo_numero,
                    pedi_forn=orcamento.pedi_forn,
                    pedi_data=date.today(),
                    pedi_tota=orcamento.pedi_tota,
                    pedi_desc=orcamento.pedi_desc,
                    pedi_topr=orcamento.pedi_topr,
                    pedi_canc=False,
                    pedi_fina='0',
                    pedi_vend=orcamento.pedi_vend or '0',
                    pedi_stat='0',
                    pedi_obse=orcamento.pedi_obse or ''
                )
                itens_orcamento = ItensOrcamento.objects.using(banco).filter(
                    iped_empr=orcamento.pedi_empr,
                    iped_fili=orcamento.pedi_fili,
                    iped_pedi=str(orcamento.pedi_nume)
                )
                for item_orcamento in itens_orcamento:
                    Itenspedidovenda.objects.using(banco).create(
                        iped_empr=item_orcamento.iped_empr,
                        iped_fili=item_orcamento.iped_fili,
                        iped_pedi=str(pedido.pedi_nume),
                        iped_item=item_orcamento.iped_item,
                        iped_prod=item_orcamento.iped_prod,
                        iped_quan=item_orcamento.iped_quan,
                        iped_unit=item_orcamento.iped_unit,
                        iped_suto=item_orcamento.iped_unit,
                        iped_tota=item_orcamento.iped_tota,
                        iped_fret=0,
                        iped_desc=item_orcamento.iped_desc,
                        iped_unli=item_orcamento.iped_unli,
                        iped_forn=item_orcamento.iped_forn,
                        iped_vend=None,
                        iped_cust=0,
                        iped_tipo=None,
                        iped_desc_item=False,
                        iped_perc_desc=item_orcamento.iped_pdes_item,
                        iped_unme=None,
                    )
                orcamento.pedi_nume_pedi = pedido.pedi_nume
                orcamento.save(using=banco)
                logger.info(f"Orçamento {orcamento.pedi_nume} transformado em pedido {pedido.pedi_nume}")
                return Response({
                    'sucesso': True,
                    'mensagem': f'Orçamento {orcamento.pedi_nume} transformado em pedido {pedido.pedi_nume} com sucesso',
                    'numero_pedido': pedido.pedi_nume,
                    'orcamento_numero': orcamento.pedi_nume
                }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Erro ao transformar orçamento em pedido: {e}")
            return Response({'error': f'Erro ao transformar orçamento em pedido: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get', 'patch'], url_path='parametros-desconto')
    def parametros_desconto(self, request, slug=None):
        try:
            if request.method == 'GET':
                empresa_id = request.query_params.get('empresa_id') or request.query_params.get('empr')
                filial_id = request.query_params.get('filial_id') or request.query_params.get('fili')
                if not empresa_id or not filial_id:
                    return Response({'error': 'empresa_id/empr e filial_id/fili são obrigatórios'}, status=status.HTTP_400_BAD_REQUEST)
                parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
                parametros_desconto = {
                    'desconto_item_disponivel': parametros.get('desconto_item_pedido', {}).get('ativo', False),
                    'desconto_total_disponivel': parametros.get('desconto_total_disponivel', {}).get('ativo', False),
                    'desconto_item_orcamento': parametros.get('desconto_item_orcamento', {}).get('ativo', False),
                    'desconto_item_pedido': parametros.get('desconto_item_pedido', {}).get('ativo', False),
                }
                return Response(parametros_desconto)
            else:
                data = request.data
                empresa_id = data.get('empresa_id')
                filial_id = data.get('filial_id')
                params_to_update = data.get('parametros', {})
                if not empresa_id or not filial_id:
                    return Response({'error': 'empresa_id e filial_id são obrigatórios'}, status=status.HTTP_400_BAD_REQUEST)
                atualizar_parametros_pedidos(empresa_id, filial_id, params_to_update, request)
                return Response({'sucesso': True})
        except Exception as e:
            logger.error(f"[parametros_desconto] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)