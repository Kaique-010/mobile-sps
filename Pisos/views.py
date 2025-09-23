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
from core.registry import get_licenca_db_config
from core.decorator import ModuloRequeridoMixin
from Produtos.models import Produtos, Tabelaprecos
from Entidades.models import Entidades

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
            
            if orcamento.orca_stat == 2:  # Já exportado
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
    
    def get_preco_produto(self, produto_id, cliente_id, condicao_pagamento='0'):
        """Obtém o preço do produto baseado na condição de pagamento"""
        try:
            banco = self.get_banco()
            
            # Buscar na tabela de preços
            tabelaprecos = Tabelaprecos.objects.using(banco).filter(
                tabe_prod=produto_id
            ).first()
            
            if not tabelaprecos:
                logger.warning(f"Preço não encontrado para produto: {produto_id}")
                return None
            
            # Retornar preço baseado na condição
            if condicao_pagamento == '0':  # À vista
                preco = tabelaprecos.tabe_avis
                logger.info(f"Preço à vista: {preco}")
            else:  # A prazo
                preco = tabelaprecos.tabe_apra or tabelaprecos.tabe_prco
                logger.info(f"Preço a prazo: {preco}")
            
            return preco
            
        except Exception as e:
            logger.error(f"Erro ao buscar preço: {e}")
            return None
    
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
        try:
            # Log dos dados recebidos para debug
            logger.info(f"Dados recebidos: {request.data}")
            
            # Obter dados do request
            produto_id = request.data.get('produto_id')
            tamanho_m2 = request.data.get('tamanho_m2')
            percentual_quebra = request.data.get('percentual_quebra', 0)
            condicao = request.data.get('condicao', '0')  # '0' para à vista, outros para prazo
            
            # Log das variáveis extraídas
            logger.info(f"produto_id: {produto_id}, tamanho_m2: {tamanho_m2}, percentual_quebra: {percentual_quebra}, condicao: {condicao}")
            
            # Validações mais detalhadas
            if not produto_id:
                logger.warning("produto_id não fornecido")
                return Response({
                    'error': 'produto_id é obrigatório',
                    'details': 'O campo produto_id deve ser fornecido'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            if tamanho_m2 is None:
                logger.warning("tamanho_m2 não fornecido")
                return Response({
                    'error': 'tamanho_m2 é obrigatório',
                    'details': 'O campo tamanho_m2 deve ser fornecido'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                tamanho_m2 = float(tamanho_m2)
                percentual_quebra = float(percentual_quebra)
                
                if tamanho_m2 <= 0:
                    return Response({
                        'error': 'tamanho_m2 deve ser maior que zero',
                        'details': f'Valor fornecido: {tamanho_m2}'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except (ValueError, TypeError) as e:
                logger.error(f"Erro na conversão de números: {e}")
                return Response({
                    'error': 'tamanho_m2 e percentual_quebra devem ser números válidos',
                    'details': f'tamanho_m2: {request.data.get("tamanho_m2")}, percentual_quebra: {request.data.get("percentual_quebra")}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Buscar produto
            try:
                banco = self.get_banco()
                produto = Produtos.objects.using(banco).get(prod_codi=produto_id)
                logger.info(f"Produto encontrado: {produto.prod_nome}")
            except Produtos.DoesNotExist:
                logger.error(f"Produto não encontrado: {produto_id}")
                return Response({
                    'error': 'Produto não encontrado',
                    'details': f'Produto com código {produto_id} não existe'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Calcular metragem total (tamanho + percentual de quebra)
            metragem_total = tamanho_m2 * (1 + percentual_quebra / 100)
            print(f"Metragem total: {metragem_total}")
            
            # Função para conversão segura de Decimal
            def safe_decimal(value, default=0):
                if value is None:
                    return default
                try:
                    if isinstance(value, str):
                        value = value.strip()
                        if not value:
                            return default
                        # Converter formato brasileiro (vírgula) para formato padrão (ponto)
                        value = value.replace(',', '.')
                    return float(Decimal(str(value)))
                except (InvalidOperation, ValueError, TypeError):
                    logger.warning(f"Erro na conversão decimal: {value}")
                    return default
            
            # Obter valores do produto (verificar se existem e não são None)
            m2_por_caixa = safe_decimal(produto.prod_cera_m2cx)
            pecas_por_caixa = safe_decimal(produto.prod_cera_pccx)
            
            logger.info(f"m2_por_caixa: {m2_por_caixa}, pecas_por_caixa: {pecas_por_caixa}")
            
            if m2_por_caixa <= 0:
                return Response({
                    'error': 'Produto não possui informação de m²/caixa válida',
                    'details': f'Valor atual: {produto.prod_cera_m2cx}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Calcular quantidade de caixas necessárias
            caixas_necessarias = math.ceil(metragem_total / m2_por_caixa)
            print(f"Caixas necessárias: {caixas_necessarias}")
            
            # Calcular peças necessárias (only if pecas_por_caixa > 0)
            if pecas_por_caixa > 0:
                pecas_necessarias = caixas_necessarias * pecas_por_caixa
            else:
                pecas_necessarias = 0  # For area-based products or services
            
            # Obter preço baseado na condição
            try:
                preco_unitario = self.get_preco_produto(produto_id, None, condicao)
                logger.info(f"Preço unitário encontrado: {preco_unitario}")
            except Exception as e:
                logger.error(f"Erro ao obter preço: {e}")
                preco_unitario = None
            
            if preco_unitario is None:
                return Response({
                    'error': 'Preço não encontrado para este produto',
                    'details': f'Produto: {produto_id}, Condição: {condicao}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Calcular valor total
            valor_total = float(preco_unitario) * caixas_necessarias
            
            resultado = {
                'produto_id': produto_id,
                'produto_nome': produto.prod_nome,
                'tamanho_ambiente_m2': tamanho_m2,
                'percentual_quebra': percentual_quebra,
                'metragem_total': round(metragem_total, 2),
                'm2_por_caixa': m2_por_caixa,
                'pecas_por_caixa': int(pecas_por_caixa) if pecas_por_caixa > 0 else 0,
                'caixas_necessarias': caixas_necessarias,
                'pecas_necessarias': int(pecas_necessarias),
                'condicao_pagamento': 'À Vista' if condicao == '0' else 'A Prazo',
                'preco_unitario': float(preco_unitario),
                'valor_total': round(valor_total, 2)
            }
            
            logger.info(f"Resultado calculado: {resultado}")
            return Response(resultado)
            
        except Exception as e:
            logger.error(f"Erro no cálculo de metragem: {str(e)}", exc_info=True)
