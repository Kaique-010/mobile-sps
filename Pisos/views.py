from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
import logging
from decimal import Decimal, InvalidOperation
import math
from .models import Orcamentopisos, Pedidospisos, Itensorcapisos, Itenspedidospisos                            
from .serializers import (
    OrcamentopisosSerializer, 
    PedidospisosSerializer, 
    ItensorcapisosSerializer, 
    ItenspedidospisosSerializer
)
from types import SimpleNamespace
from core.registry import get_licenca_db_config
from core.decorator import ModuloRequeridoMixin
from Produtos.models import Produtos, Tabelaprecos
from Entidades.models import Entidades
from .preco_service import get_preco_produto
from .utils_service import parse_decimal, arredondar
from .calculo_services import calcular_item, calcular_ambientes, calcular_total_geral
import logging

logger = logging.getLogger(__name__)

class BaseMultiDBModelViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_banco(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error(f"Banco de dados não encontrado para {self.__class__.__name__}")
            raise NotFound("Banco de dados não encontrado.")
        return banco

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context


class OrcamentopisosViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'Pisos'
    serializer_class = OrcamentopisosSerializer
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['orca_nume', 'orca_clie']
    filterset_fields = [
        'orca_empr', 'orca_fili', 'orca_nume', 'orca_clie', 
        'orca_data', 'orca_stat', 'orca_vend'
    ]
    lookup_field = 'orca_nume'
    
    def get_queryset(self):
        banco = self.get_banco()
        queryset = Orcamentopisos.objects.using(banco).all()
        
        # Filtros por parâmetros de query
        empresa_id = self.request.query_params.get('orca_empr')
        filial_id = self.request.query_params.get('orca_fili')
        cliente_id = self.request.query_params.get('orca_clie')
        
        if empresa_id:
            queryset = queryset.filter(orca_empr=empresa_id)
        if filial_id:
            queryset = queryset.filter(orca_fili=filial_id)
        if cliente_id:
            queryset = queryset.filter(orca_clie=cliente_id)
            
        return queryset.order_by('-orca_data', '-orca_nume')
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        logger.info(f"[OrcamentopisosViewSet.create] Criando orçamento de pisos")
        
        banco = self.get_banco()
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            
            # Gerar próximo número do orçamento
            ultimo = Orcamentopisos.objects.using(banco).filter(
                orca_empr=serializer.validated_data['orca_empr'],
                orca_fili=serializer.validated_data['orca_fili']
            ).order_by('-orca_nume').first()
            
            proximo_numero = (ultimo.orca_nume + 1) if ultimo else 1
            serializer.validated_data['orca_nume'] = proximo_numero
            
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        except ValidationError as e:
            logger.warning(f"[OrcamentopisosViewSet.create] Erro de validação: {e.detail}")
            return Response({'errors': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"[OrcamentopisosViewSet.create] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def exportar_pedido(self, request, orca_nume=None):
        """Converte orçamento em pedido"""
        banco = self.get_banco()
        
        try:
            orcamento = self.get_object()
            
            if orcamento.orca_stat == 2:  
                return Response(
                    {'error': 'Orçamento já foi exportado para pedido'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Criar pedido baseado no orçamento
            ultimo_pedido = Pedidospisos.objects.using(banco).filter(
                pedi_empr=orcamento.orca_empr,
                pedi_fili=orcamento.orca_fili
            ).order_by('-pedi_nume').first()
            
            proximo_numero_pedido = (ultimo_pedido.pedi_nume + 1) if ultimo_pedido else 1
            
            # Dados do pedido baseados no orçamento
            dados_pedido = {
                'pedi_empr': orcamento.orca_empr,
                'pedi_fili': orcamento.orca_fili,
                'pedi_nume': proximo_numero_pedido,
                'pedi_clie': orcamento.orca_clie,
                'pedi_data': orcamento.orca_data,
                'pedi_tota': orcamento.orca_tota,
                'pedi_obse': orcamento.orca_obse,
                'pedi_vend': orcamento.orca_vend,
                'pedi_desc': orcamento.orca_desc,
                'pedi_fret': orcamento.orca_fret,
                'pedi_ende': orcamento.orca_ende,
                'pedi_nume_ende': orcamento.orca_nume_ende,
                'pedi_comp': orcamento.orca_comp,
                'pedi_bair': orcamento.orca_bair,
                'pedi_cida': orcamento.orca_cida,
                'pedi_esta': orcamento.orca_esta,
                'pedi_orca': orcamento.orca_nume,
                # Copiar todos os campos específicos de pisos
                'pedi_mode_piso': orcamento.orca_mode_piso,
                'pedi_mode_alum': orcamento.orca_mode_alum,
                'pedi_mode_roda': orcamento.orca_mode_roda,
                'pedi_mode_port': orcamento.orca_mode_port,
                'pedi_mode_outr': orcamento.orca_mode_outr,
                'pedi_sent_piso': orcamento.orca_sent_piso,
                'pedi_ajus_port': orcamento.orca_ajus_port,
                'pedi_degr_esca': orcamento.orca_degr_esca,
                'pedi_obra_habi': orcamento.orca_obra_habi,
                'pedi_movi_mobi': orcamento.orca_movi_mobi,
                'pedi_remo_roda': orcamento.orca_remo_roda,
                'pedi_remo_carp': orcamento.orca_remo_carp,
                'pedi_croq_info': orcamento.orca_croq_info,
                'pedi_stat': 0,  # Status inicial do pedido
            }
            
            pedido = Pedidospisos.objects.using(banco).create(**dados_pedido)
            
            # Copiar itens do orçamento para o pedido
            itens_orcamento = Itensorcapisos.objects.using(banco).filter(
                item_empr=orcamento.orca_empr,
                item_fili=orcamento.orca_fili,
                item_orca=orcamento.orca_nume
            )
            
            for item_orc in itens_orcamento:
                Itenspedidospisos.objects.using(banco).create(
                    item_empr=pedido.pedi_empr,
                    item_fili=pedido.pedi_fili,
                    item_pedi=pedido.pedi_nume,
                    item_ambi=item_orc.item_ambi,
                    item_prod=item_orc.item_prod,
                    item_m2=item_orc.item_m2,
                    item_quan=item_orc.item_quan,
                    item_unit=item_orc.item_unit,
                    item_suto=item_orc.item_suto,
                    item_obse=item_orc.item_obse,
                    item_nome_ambi=item_orc.item_nome_ambi,
                    item_nume=item_orc.item_nume,
                    item_caix=item_orc.item_caix,
                    item_desc=item_orc.item_desc,
                    item_queb=item_orc.item_queb,
                    item_inst_incl=item_orc.item_inst_incl,
                )
            
            # Atualizar status do orçamento
            orcamento.orca_stat = 2  # Exportado para pedido
            orcamento.orca_pedi = pedido.pedi_nume
            orcamento.save(using=banco)
            
            return Response({
                'message': 'Orçamento exportado para pedido com sucesso',
                'pedido_numero': pedido.pedi_nume
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Erro ao exportar orçamento para pedido: {e}")
            return Response(
                {'error': 'Erro ao exportar orçamento para pedido'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PedidospisosViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'Pisos'
    serializer_class = PedidospisosSerializer
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['pedi_nume', 'pedi_clie']
    filterset_fields = [
        'pedi_empr', 'pedi_fili', 'pedi_nume', 'pedi_clie', 
        'pedi_data', 'pedi_stat', 'pedi_vend', 'pedi_orca'
    ]
    lookup_field = 'pedi_nume'
    
    def get_queryset(self):
        banco = self.get_banco()
        queryset = Pedidospisos.objects.using(banco).all()
        
        # Filtros por parâmetros de query
        empresa_id = self.request.query_params.get('pedi_empr')
        filial_id = self.request.query_params.get('pedi_fili')
        cliente_id = self.request.query_params.get('pedi_clie')
        
        if empresa_id:
            queryset = queryset.filter(pedi_empr=empresa_id)
        if filial_id:
            queryset = queryset.filter(pedi_fili=filial_id)
        if cliente_id:
            queryset = queryset.filter(pedi_clie=cliente_id)
            
        return queryset.order_by('-pedi_data', '-pedi_nume')
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        logger.info(f"[PedidospisosViewSet.create] Criando pedido de pisos")
        
        banco = self.get_banco()
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            
            # Gerar próximo número do pedido
            ultimo = Pedidospisos.objects.using(banco).filter(
                pedi_empr=serializer.validated_data['pedi_empr'],
                pedi_fili=serializer.validated_data['pedi_fili']
            ).order_by('-pedi_nume').first()
            
            proximo_numero = (ultimo.pedi_nume + 1) if ultimo else 1
            serializer.validated_data['pedi_nume'] = proximo_numero
            
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        except ValidationError as e:
            logger.warning(f"[PedidospisosViewSet.create] Erro de validação: {e.detail}")
            return Response({'errors': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"[PedidospisosViewSet.create] Erro inesperado: {e}")
            return Response({'error': 'Erro interno do servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ItensorcapisosViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'Pisos'
    serializer_class = ItensorcapisosSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'item_empr', 'item_fili', 'item_orca', 'item_ambi', 'item_prod'
    ]
    
    def get_queryset(self):
        banco = self.get_banco()
        queryset = Itensorcapisos.objects.using(banco).all()
        
        # Filtros obrigatórios para performance
        item_empr = self.request.query_params.get('item_empr')
        item_fili = self.request.query_params.get('item_fili')
        item_orca = self.request.query_params.get('item_orca')
        
        if item_empr:
            queryset = queryset.filter(item_empr=item_empr)
        if item_fili:
            queryset = queryset.filter(item_fili=item_fili)
        if item_orca:
            queryset = queryset.filter(item_orca=item_orca)
            
        return queryset.order_by('item_ambi', 'item_nume')


class ItenspedidospisosViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'Pisos'
    serializer_class = ItenspedidospisosSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'item_empr', 'item_fili', 'item_pedi', 'item_ambi', 'item_prod'
    ]
    
    def get_queryset(self):
        banco = self.get_banco()
        queryset = Itenspedidospisos.objects.using(banco).all()
        
        # Filtros obrigatórios para performance
        item_empr = self.request.query_params.get('item_empr')
        item_fili = self.request.query_params.get('item_fili')
        item_pedi = self.request.query_params.get('item_pedi')
        
        if item_empr:
            queryset = queryset.filter(item_empr=item_empr)
        if item_fili:
            queryset = queryset.filter(item_fili=item_fili)
        if item_pedi:
            queryset = queryset.filter(item_pedi=item_pedi)
            
        return queryset.order_by('item_ambi', 'item_nume')


# ViewSet para buscar produtos para cálculos (baseado nas imagens do sistema legado)
class ProdutosPisosViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'Pisos'
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['prod_nome', 'prod_codi', 'prod_coba']
    filterset_fields = ['prod_empr']
    
    def get_queryset(self):
        banco = self.get_banco()
        return Produtos.objects.using(banco).all().order_by('prod_nome')
    
    def get_serializer_class(self):
        # Usar o serializer de produtos existente
        from Produtos.serializers import ProdutoSerializer
        return ProdutoSerializer
    
    def item_prod_nome(self, item_prod):
        try:
            banco = self.get_banco()
            produto = Produtos.objects.using(banco).filter(prod_codi=item_prod).first()
            if produto:
                return produto.prod_nome
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar nome do produto: {e}")
            return None
    
    @action(detail=False, methods=['post'])
    def calcular_metragem(self, request, slug=None):
        banco = self.get_banco()
        produto_id = request.data.get('produto_id')
        tamanho_m2 = request.data.get('tamanho_m2')
        percentual_quebra = request.data.get('percentual_quebra', 0)
        condicao = request.data.get('condicao', '0')

        try:
            produto = Produtos.objects.using(banco).get(prod_codi=produto_id)
        except Produtos.DoesNotExist:
            return Response({'error': 'Produto não encontrado'}, status=status.HTTP_404_NOT_FOUND)

        # 1️⃣ cálculo físico
        calculo = calcular_item(SimpleNamespace(
            item_m2=tamanho_m2,
            item_queb=percentual_quebra,
            item_unit=0,
        ), produto)

        preco_origem = "tabela"
        try:
            preco_unitario = get_preco_produto(banco, produto_id, condicao)
        except Exception as e:
            logger.warning(f"[calcular_metragem] Preço não encontrado na tabela: {e}. Usando fallback do produto.")
            preco_origem = "fallback_produto"
            # Tentar usar um preço do próprio produto (se existir), senão 0
            preco_unitario = parse_decimal(getattr(produto, "prod_prec", 0))

        valor_total = arredondar(parse_decimal(calculo["metragem_real"]) * parse_decimal(preco_unitario))


        prod_m2cx_attr = getattr(produto, "prod_cera_m2cx", None)
        m2_por_caixa = parse_decimal(prod_m2cx_attr) if prod_m2cx_attr is not None else None
        resultado = {
            **calculo,
            "produto_id": produto_id,
            "produto_nome": produto.prod_nome,
            "condicao_pagamento": "À Vista" if condicao == "0" else "A Prazo",
            "preco_unitario": preco_unitario,
            "valor_total": valor_total,
            "m2_por_caixa": m2_por_caixa,
            "metragem_total": calculo.get("metragem_real"),
            "preco_origem": preco_origem,
        }
        
        resultado["total"] = valor_total
        print(resultado)

        return Response(resultado)