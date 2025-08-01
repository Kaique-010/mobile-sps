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

from .models import Orcamentos, ItensOrcamento
from .serializers import OrcamentosSerializer
from Entidades.models import Entidades
from Pedidos.models import PedidoVenda, Itenspedidovenda
from core.utils import get_licenca_db_config

logger = logging.getLogger('Orcamentos')

class OrcamentoViewSet(viewsets.ModelViewSet):
    serializer_class = OrcamentosSerializer
    lookup_field = 'pedi_nume'
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['pedi_forn', 'pedi_nume']
    filterset_fields = ['pedi_empr', 'pedi_fili', 'pedi_nume', 'pedi_forn', 'pedi_data']

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")
            
        # Base queryset otimizada
        queryset = Orcamentos.objects.using(banco).all()
        
        # Aplicar filtros de forma otimizada
        cliente_nome = self.request.query_params.get('cliente_nome')
        numero_orcamento = self.request.query_params.get('pedi_nume')
        empresa_id = self.request.query_params.get('pedi_empr')
        filial_id = self.request.query_params.get('pedi_fili')

        # Filtros mais específicos primeiro
        if empresa_id:
            queryset = queryset.filter(pedi_empr=empresa_id)
            
        if filial_id:
            queryset = queryset.filter(pedi_fili=filial_id)

        if numero_orcamento:
            try:
                numero = int(numero_orcamento)
                queryset = queryset.filter(pedi_nume=numero)
            except ValueError:
                return queryset.none()

        # Filtro por nome do cliente (mais custoso, por último)
        if cliente_nome:
            # Cache para consultas de entidades
            cache_key = f"entidades_cliente_{cliente_nome}_{empresa_id}"
            entidades_ids = cache.get(cache_key)
            
            if entidades_ids is None:
                # Otimizar consulta de entidades
                entidades_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=cliente_nome)
                    .filter(enti_empr=empresa_id if empresa_id else None)
                    .values_list('enti_clie', flat=True)[:100]  # Limitar resultados
                )
                # Cache por 5 minutos
                cache.set(cache_key, entidades_ids, 300)
            
            if entidades_ids:
                queryset = queryset.filter(pedi_forn__in=entidades_ids)
            else:
                return queryset.none()

        # Ordenar por número do orçamento (mais recentes primeiro)
        return queryset.order_by('-pedi_nume')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

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
                # Verificar se há itens associados
                itens_count = ItensOrcamento.objects.using(banco).filter(
                    iped_empr=orcamento.pedi_empr,
                    iped_fili=orcamento.pedi_fili,
                    iped_pedi=str(orcamento.pedi_nume)
                ).count()
                
                if itens_count > 0:
                    # Excluir itens primeiro
                    ItensOrcamento.objects.using(banco).filter(
                        iped_empr=orcamento.pedi_empr,
                        iped_fili=orcamento.pedi_fili,
                        iped_pedi=str(orcamento.pedi_nume)
                    ).delete()
                    logger.info(f"Excluídos {itens_count} itens do orçamento {orcamento.pedi_nume}")
                
                # Excluir orçamento
                orcamento.delete()
                logger.info(f"🗑️ Exclusão Orçamento ID {orcamento.pedi_nume} concluída")

            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"[OrcamentoViewSet.destroy] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='transformar-em-pedido')
    def transformar_em_pedido(self, request, pedi_nume=None, slug=None):
        """
        Transforma um orçamento em pedido de venda
        """
        try:
            orcamento = self.get_object()
            banco = get_licenca_db_config(request)
            
            if not banco:
                return Response(
                    {'erro': 'Banco de dados não encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            with transaction.atomic(using=banco):
                # Obter próximo número de pedido
                ultimo_pedido = PedidoVenda.objects.using(banco).filter(
                    pedi_empr=orcamento.pedi_empr,
                    pedi_fili=orcamento.pedi_fili
                ).order_by('-pedi_nume').first()
                
                proximo_numero = (ultimo_pedido.pedi_nume + 1) if ultimo_pedido else 1
                
                # Verificar se o número já existe
                while PedidoVenda.objects.using(banco).filter(pedi_nume=proximo_numero).exists():
                    proximo_numero += 1
                
                # Criar pedido
                pedido = PedidoVenda.objects.using(banco).create(
                    pedi_empr=orcamento.pedi_empr,
                    pedi_fili=orcamento.pedi_fili,
                    pedi_nume=proximo_numero,
                    pedi_forn=orcamento.pedi_forn,
                    pedi_data=date.today(),
                    pedi_tota=orcamento.pedi_tota,
                    pedi_canc=False,
                    pedi_fina='0',  # À vista por padrão
                    pedi_vend=orcamento.pedi_vend or '0',
                    pedi_stat='0',  # Pendente
                    pedi_obse=orcamento.pedi_obse or ''
                )
                
                # Buscar itens do orçamento
                itens_orcamento = ItensOrcamento.objects.using(banco).filter(
                    iped_empr=orcamento.pedi_empr,
                    iped_fili=orcamento.pedi_fili,
                    iped_pedi=str(orcamento.pedi_nume)
                )
                
                # Criar itens do pedido
                for item_orcamento in itens_orcamento:
                    Itenspedidovenda.objects.using(banco).create(
                        iped_empr=item_orcamento.iped_empr,
                        iped_fili=item_orcamento.iped_fili,
                        iped_pedi=str(pedido.pedi_nume),
                        iped_item=item_orcamento.iped_item,
                        iped_prod=item_orcamento.iped_prod,
                        iped_quan=item_orcamento.iped_quan,
                        iped_unit=item_orcamento.iped_unit,
                        iped_suto=item_orcamento.iped_unit,  # Subtotal = unit por padrão
                        iped_tota=item_orcamento.iped_tota,
                        iped_fret=0,  # Frete padrão
                        iped_desc=item_orcamento.iped_desc,
                        iped_unli=item_orcamento.iped_unli,
                        iped_forn=item_orcamento.iped_forn,
                        iped_vend=None,  # Vendedor será definido depois
                        iped_cust=0,  # Custo padrão
                        iped_tipo=None,  # Tipo padrão
                        iped_desc_item=False,  # Sem desconto por item por padrão
                        iped_perc_desc=item_orcamento.iped_pdes_item,  # Mapear corretamente
                        iped_unme=None,  # Unidade de medida padrão
                        # iped_data será definido automaticamente
                    )
                
                # Atualizar orçamento com número do pedido gerado
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
            return Response(
                {'error': f'Erro ao transformar orçamento em pedido: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        