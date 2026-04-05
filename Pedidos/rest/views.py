import logging
from django.db import transaction
from django.core.cache import cache
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from ..models import PedidoVenda, Itenspedidovenda
from .serializers import PedidoVendaSerializer
from core.mixins.vendedor_mixin import VendedorEntidadeMixin
from Entidades.models import Entidades
from Licencas.models import Empresas
from core.utils import get_licenca_db_config
from rest_framework.permissions import IsAuthenticated
from parametros_admin.decorators import parametros_pedidos_completo
from parametros_admin.utils_pedidos import obter_parametros_pedidos, atualizar_parametros_pedidos
from ..services.pedido_service import PedidoVendaService
from .handlers.dominio_handler import tratar_erro

logger = logging.getLogger('Pedidos')

class PedidoVendaViewSet(viewsets.ModelViewSet, VendedorEntidadeMixin):
    permission_classes = [IsAuthenticated]
    modulo_requerido = 'Pedidos'
    serializer_class = PedidoVendaSerializer
    lookup_field = 'pedi_nume'
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['pedi_forn', 'pedi_nume']
    filterset_fields = ['pedi_empr', 'pedi_fili', 'pedi_nume', 'pedi_forn', 'pedi_data', 'pedi_stat']

    def get_object(self):
        try:
            empresa = self.kwargs.get('empresa') or self.kwargs.get('pedi_empr')
            filial = self.kwargs.get('filial') or self.kwargs.get('pedi_fili')
            numero = self.kwargs.get('numero') or self.kwargs.get('pedi_nume')

            if not empresa:
                empresa = self.request.query_params.get('empresa') or self.request.query_params.get('pedi_empr')
            if not filial:
                filial = self.request.query_params.get('filial') or self.request.query_params.get('pedi_fili')
            if not numero:
                numero = self.request.query_params.get('numero') or self.request.query_params.get('pedi_nume')

            if not empresa and hasattr(self.request, 'data'):
                empresa = self.request.data.get('empresa') or self.request.data.get('pedi_empr')
            if not filial and hasattr(self.request, 'data'):
                filial = self.request.data.get('filial') or self.request.data.get('pedi_fili')
            if not numero and hasattr(self.request, 'data'):
                numero = self.request.data.get('numero') or self.request.data.get('pedi_nume')

            logger.debug(f"Parâmetros recebidos - Empresa: {empresa}, Filial: {filial}, Numero: {numero}")

            if not all([empresa, filial, numero]):
                raise ValidationError("Empresa, filial e número são obrigatórios")

            banco = get_licenca_db_config(self.request)
            base_qs = PedidoVenda.objects.using(banco)
            base_qs = self.filter_por_vendedor(base_qs, 'pedi_vend')
            pedido = get_object_or_404(base_qs, pedi_empr=empresa, pedi_fili=filial, pedi_nume=numero)

            return pedido

        except PedidoVenda.DoesNotExist:
            raise NotFound("Pedido não encontrado")
        except Exception as e:
            logger.error(f"Erro ao buscar pedido: {e}")
            raise ValidationError(f"Erro ao buscar pedido: {str(e)}")

    def get_queryset(self):
        from datetime import datetime

        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        queryset = PedidoVenda.objects.using(banco)
        queryset = self.filter_por_vendedor(queryset, 'pedi_vend')

        cliente_nome = self.request.query_params.get('cliente_nome')
        numero_pedido = self.request.query_params.get('pedi_nume')
        empresa_id = self.request.query_params.get('pedi_empr')
        filial_id = self.request.query_params.get('pedi_fili')

        tem_filtros_especificos = cliente_nome or numero_pedido

        if not tem_filtros_especificos:
            ano_atual = datetime.now().year
            queryset = queryset.filter(pedi_data__year=ano_atual)
            logger.info(f"Aplicando filtro por ano atual: {ano_atual}")

        if empresa_id:
            queryset = queryset.filter(pedi_empr=empresa_id)

        if filial_id:
            queryset = queryset.filter(pedi_fili=filial_id)

        if numero_pedido:
            try:
                numero = int(numero_pedido)
                queryset = queryset.filter(pedi_nume=numero)
                logger.info(f"Buscando pedido específico: {numero} (sem filtro de ano)")
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

        print(f"nome do cliente: {cliente_nome}")

        return queryset.order_by('-pedi_nume')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def list(self, request, *args, **kwargs):
        try:
            banco = get_licenca_db_config(request)
            if not banco:
                logger.error("Banco de dados não encontrado.")
                raise NotFound("Banco de dados não encontrado.")

            queryset = self.filter_queryset(self.get_queryset())

            page = self.paginate_queryset(queryset)
            if page is not None:
                empresas_ids = list(set([p.pedi_empr for p in page]))
                fornecedores_ids = list(set([p.pedi_forn for p in page]))

                empresas_cache = {}
                if empresas_ids:
                    empresas = Empresas.objects.using(banco).filter(empr_codi__in=empresas_ids)
                    empresas_cache = {emp.empr_codi: emp.empr_nome for emp in empresas}

                entidades_cache = {}
                if fornecedores_ids and empresas_ids:
                    entidades = Entidades.objects.using(banco).filter(
                        enti_clie__in=fornecedores_ids,
                        enti_empr__in=empresas_ids
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
            return tratar_erro(e)

    @parametros_pedidos_completo
    def create(self, request, *args, **kwargs):
        logger.info(f"🎯 [CREATE] Iniciando criação de pedido")
        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())

        try:
            serializer.is_valid(raise_exception=True)
            pedido = serializer.save()
            logger.info(f"✅ Pedido {pedido.pedi_nume} criado com sucesso")

            headers = self.get_success_headers(serializer.data)
            return Response(
                {'pedido': serializer.data},
                status=status.HTTP_201_CREATED,
                headers=headers
            )
        except Exception as e:
            return tratar_erro(e)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception as e:
            return tratar_erro(e)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except Exception as e:
            return tratar_erro(e)

    def destroy(self, request, *args, **kwargs):
        try:
            pedido = self.get_object()
            banco = get_licenca_db_config(self.request)

            if not banco:
                logger.error("Banco de dados não encontrado.")
                raise NotFound("Banco de dados não encontrado.")

            try:
                resultado_estoque = PedidoVendaService.estornar_estoque_pedido(pedido, banco=banco)
                if not resultado_estoque.get('sucesso', True):
                    logger.warning(f"Erro ao reverter estoque: {resultado_estoque.get('erro')}")
                elif resultado_estoque.get('processado'):
                    logger.info(f"Estoque revertido para pedido {pedido.pedi_nume}")
            except Exception as e:
                logger.error(f"Erro ao reverter estoque: {e}")

            with transaction.atomic(using=banco):
                Itenspedidovenda.objects.using(banco).filter(
                    iped_empr=pedido.pedi_empr,
                    iped_fili=pedido.pedi_fili,
                    iped_pedi=str(pedido.pedi_nume)
                ).delete()

                pedido.delete()
                logger.info(f"🗑️ Exclusão Pedido ID {pedido.pedi_nume} concluída")

            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return tratar_erro(e)

    @action(detail=False, methods=['get'], url_path='lotes-produto')
    def lotes_produto(self, request, *args, **kwargs):
        try:
            banco = get_licenca_db_config(request)
            if not banco:
                raise NotFound("Banco de dados não encontrado.")

            empresa_id = (
                request.query_params.get('empresa')
                or request.query_params.get('pedi_empr')
                or request.query_params.get('lote_empr')
                or request.session.get('empresa_id', 1)
            )
            prod_codi = (request.query_params.get('prod_codi') or request.query_params.get('produto') or '').strip()
            if not prod_codi:
                raise ValidationError("prod_codi é obrigatório")

            from Produtos.models import Lote

            lotes_qs = (
                Lote.objects.using(banco)
                .filter(
                    lote_empr=int(empresa_id),
                    lote_prod=str(prod_codi),
                    lote_ativ=True,
                )
                .order_by('lote_data_vali', 'lote_lote')
            )

            lotes = []
            from decimal import Decimal
            saldo_lotes = Decimal("0")
            for row in lotes_qs.values('lote_lote', 'lote_sald', 'lote_data_fabr', 'lote_data_vali', 'lote_obse')[:200]:
                saldo_lotes += Decimal(str(row.get('lote_sald') or 0))
                lotes.append(
                    {
                        'lote_lote': int(row.get('lote_lote')),
                        'lote_sald': float(row.get('lote_sald') or 0),
                        'lote_data_fabr': row.get('lote_data_fabr'),
                        'lote_data_vali': row.get('lote_data_vali'),
                        'lote_obse': row.get('lote_obse'),
                    }
                )

            filial_id = (
                request.query_params.get('filial')
                or request.query_params.get('pedi_fili')
                or request.query_params.get('lote_fili')
                or request.session.get('filial_id', 1)
            )
            from Produtos.models import SaldoProduto
            sp = (
                SaldoProduto.objects.using(banco)
                .filter(produto_codigo_id=str(prod_codi), empresa=str(empresa_id), filial=str(filial_id))
                .first()
            )
            saldo_total = Decimal(str(getattr(sp, 'saldo_estoque', 0) or 0))
            saldo_sem_lote = saldo_total - saldo_lotes

            return Response({
                'results': lotes,
                'saldo_total': float(saldo_total),
                'saldo_lotes': float(saldo_lotes),
                'saldo_sem_lote': float(saldo_sem_lote),
            })
        except Exception as e:
            return tratar_erro(e)

    @action(detail=False, methods=['get'], url_path='lotes-produtos-desc')
    def lotes_produtos_desc(self, request, *args, **kwargs):
        try:
            banco = get_licenca_db_config(request)
            if not banco:
                raise NotFound("Banco de dados não encontrado.")

            empresa_id = (
                request.query_params.get('empresa')
                or request.query_params.get('pedi_empr')
                or request.query_params.get('lote_empr')
                or request.session.get('empresa_id', 1)
            )

            prod_codi = (request.query_params.get('prod_codi') or request.query_params.get('produto') or '').strip()
            if not prod_codi:
                raise ValidationError("prod_codi é obrigatório")

            qtd = request.query_params.get('qtd') or request.query_params.get('quantidade')
            qtd = float(qtd) if (qtd is not None and str(qtd).strip() != '') else None

            from Produtos.models import Lote, SaldoProduto
            from decimal import Decimal
            from django.utils import timezone

            try:
                empresa_int = int(empresa_id)
            except Exception:
                empresa_int = int(str(empresa_id or 1).strip() or 1)

            lotes_qs = (
                Lote.objects.using(banco)
                .filter(
                    lote_empr=empresa_int,
                    lote_prod=str(prod_codi),
                    lote_ativ=True,
                )
                .order_by('lote_data_vali', 'lote_data_fabr', 'lote_lote')
            )

            lotes = []
            saldo_lotes = Decimal("0")
            for row in lotes_qs.values('lote_lote', 'lote_unit', 'lote_sald', 'lote_data_fabr', 'lote_data_vali', 'lote_obse')[:500]:
                saldo_lotes += Decimal(str(row.get('lote_sald') or 0))
                data_vali = row.get('lote_data_vali')
                data_fabr = row.get('lote_data_fabr')
                status_venc = None
                if data_vali:
                    try:
                        hoje = timezone.localdate()
                    except Exception:
                        hoje = timezone.now().date()
                    if data_vali < hoje:
                        status_venc = 'VENCIDO'
                    else:
                        try:
                            delta = (data_vali - hoje).days
                        except Exception:
                            delta = None
                        if delta is not None and 0 <= delta <= 30:
                            status_venc = 'PRÓXIMO_VENCIMENTO'
                        else:
                            status_venc = 'VÁLIDO'
                lotes.append(
                    {
                        'lote_lote': int(row.get('lote_lote')),
                        'lote_unit': float(row.get('lote_unit') or 0),
                        'lote_sald': float(row.get('lote_sald') or 0),
                        'lote_data_fabr': data_fabr.isoformat() if hasattr(data_fabr, 'isoformat') else data_fabr,
                        'lote_data_vali': data_vali.isoformat() if hasattr(data_vali, 'isoformat') else data_vali,
                        'lote_obse': row.get('lote_obse'),
                        'status_vencimento': status_venc,
                    }
                )

            filial_id = (
                request.query_params.get('filial')
                or request.query_params.get('pedi_fili')
                or request.query_params.get('lote_fili')
                or request.session.get('filial_id', 1)
            )
            sp = (
                SaldoProduto.objects.using(banco)
                .filter(produto_codigo_id=str(prod_codi), empresa=str(empresa_id), filial=str(filial_id))
                .first()
            )
            saldo_total = Decimal(str(getattr(sp, 'saldo_estoque', 0) or 0))
            saldo_sem_lote = saldo_total - saldo_lotes

            consumo = []
            saldo_faltante = None
            if qtd is not None:
                restante = Decimal(str(qtd))
                for lote in lotes:
                    if restante <= 0:
                        break
                    saldo_lote = Decimal(str(lote.get('lote_sald') or 0))
                    usar = saldo_lote if saldo_lote <= restante else restante
                    restante -= usar
                    if usar > 0:
                        consumo.append(
                            {
                                'origem': 'LOTE',
                                'lote_lote': lote.get('lote_lote'),
                                'quantidade': float(usar),
                            }
                        )
                if restante > 0:
                    saldo_disponivel_sem_lote = saldo_sem_lote if saldo_sem_lote > 0 else Decimal("0")
                    usar = saldo_disponivel_sem_lote if saldo_disponivel_sem_lote <= restante else restante
                    restante -= usar
                    if usar > 0:
                        consumo.append(
                            {
                                'origem': 'SEM_LOTE',
                                'lote_lote': None,
                                'quantidade': float(usar),
                            }
                        )
                saldo_faltante = float(restante) if restante > 0 else 0.0

            return Response(
                {
                    'results': lotes,
                    'saldo_total': float(saldo_total),
                    'saldo_lotes': float(saldo_lotes),
                    'saldo_sem_lote': float(saldo_sem_lote),
                    'consumo': consumo,
                    'saldo_faltante': saldo_faltante,
                }
            )
        except Exception as e:
            return tratar_erro(e)

    @action(detail=True, methods=['post'])
    def cancelar_pedido(self, request, empresa=None, filial=None, numero=None, **kwargs):
        try:
            pedido = self.get_object()
            banco = get_licenca_db_config(request)

            if not banco:
                return Response({'erro': 'Banco de dados não encontrado'}, status=status.HTTP_404_NOT_FOUND)

            if not PedidoVendaService.pedido_cancela_nao_exclui(banco, pedido.pedi_empr):
                return Response(
                    {'erro': 'Cancelamento de pedido não está habilitado nos parâmetros.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            if pedido.pedi_stat == '4':
                return Response({'erro': 'Pedido já cancelado'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic(using=banco):
                resultado_estoque = PedidoVendaService.estornar_estoque_pedido(pedido, banco=banco)
                logger.info(f"♻️ Estoque revertido para pedido {pedido.pedi_nume}: {resultado_estoque}")

                pedido.pedi_stat = '4'
                pedido.pedi_canc = True
                pedido.save(using=banco, update_fields=['pedi_stat', 'pedi_canc'])

                return Response({
                    'sucesso': True,
                    'mensagem': f'Pedido {pedido.pedi_nume} cancelado e estoque revertido',
                    'estoque': resultado_estoque
                }, status=status.HTTP_200_OK)
        except Exception as e:
            return tratar_erro(e)
