from django.shortcuts import render
from django.db.models import Q, Count, Avg, Max
from .models import Controlevisita, Etapavisita, ItensVisita
from Orcamentos.models import Orcamentos, ItensOrcamento
from Entidades.models import Entidades
from Licencas.models import Liberar
from django.shortcuts import get_object_or_404
from .serializers import ControleVisitaSerializer, EtapaVisitaSerializer, ExportarVisitaParaOrcamentoSerializer, ItensVisitaSerializer
from .services import (
    exportar_visita_para_orcamento, 
    exportar_visita_para_orcamento_pisos, 
    verificar_modulo_pisos_liberado
)
from Pisos.services.utils_service import parse_decimal, arredondar
from Pisos.services.preco_service import get_preco_produto
from core.serializers import BancoContextMixin
from Pisos.views import BaseMultiDBModelViewSet
from Pisos.services.calculo_services import calcular_ambientes, calcular_item, calcular_total_geral
from Produtos.models import Produtos
from rest_framework import viewsets, status
from core.utils import get_licenca_db_config
from core.decorator import ModuloRequeridoMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.decorators import action
from types import SimpleNamespace
from datetime import datetime, date, timedelta
from core.mixins.vendedor_mixin import VendedorEntidadeMixin
import logging

logger = logging.getLogger(__name__)


class ControleVisitaViewSet(BancoContextMixin, ModuloRequeridoMixin, VendedorEntidadeMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    modulo_requerido = 'Pedidos'
    serializer_class = ControleVisitaSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        'ctrl_empresa', 
        'ctrl_filial', 
        'ctrl_numero',
        'ctrl_cliente', 
        'ctrl_data',
        'ctrl_vendedor',
        'ctrl_etapa'
    ]
    search_fields = [
        'ctrl_numero',
        'ctrl_cliente__enti_nome', 
        'ctrl_vendedor__enti_nome',
        'ctrl_contato',
        'ctrl_obse'
    ]
    ordering_fields = ['ctrl_data', 'ctrl_numero', 'ctrl_cliente']
    ordering = ['-ctrl_data', '-ctrl_numero']
    lookup_field = 'ctrl_id'


    
    def get_queryset(self):

        banco = get_licenca_db_config(self.request)
        print(f"🔍 DEBUG: Banco de dados configurado para licença: {banco}")
        
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")
        
        empresa_id = self.request.headers.get("X-Empresa")
        filial_id = self.request.headers.get("X-Filial")
        
        # Base queryset com select_related para otimização
        queryset = Controlevisita.objects.using(banco).select_related(
            'ctrl_cliente',
            'ctrl_vendedor', 
            'ctrl_empresa',
            'ctrl_etapa'
        ).all()

        user = self.request.user
        
        # Verificar se usuário é vendedor e filtrar suas visitas
        print(f"🔍 DEBUG: Iniciando verificação de vendedor para usuário {user.usua_nome} (ID: {user.usua_codi})")
        entidade_vendedor = self.get_entidade_vendedor(user, banco)
        print(f"🔍 DEBUG: Resultado _get_entidade_vendedor: {entidade_vendedor}")
        
        if entidade_vendedor:
            print(f"✅ Usuário {user.usua_nome} é vendedor. Filtrando visitas para entidade {entidade_vendedor.enti_clie}.")
            queryset_antes = queryset.count()
            queryset = queryset.filter(ctrl_vendedor=entidade_vendedor.enti_clie)
            queryset_depois = queryset.count()
            print(f"🎯 Queryset filtrado aplicado: ctrl_vendedor={entidade_vendedor.enti_clie}")
            print(f"📊 DEBUG: Registros antes do filtro: {queryset_antes}, depois: {queryset_depois}")
        else:
            print(f"❌ Usuário {user.usua_nome} não é vendedor. Acesso total permitido.")
        
        
        # Filtros por headers
        if empresa_id:
            queryset = queryset.filter(ctrl_empresa=empresa_id)
        if filial_id:
            queryset = queryset.filter(ctrl_filial=filial_id)
        
        # Filtros por query params
        cliente_nome = self.request.query_params.get('cliente_nome')
        vendedor_nome = self.request.query_params.get('vendedor_nome')
        data_inicio = self.request.query_params.get('data_inicio')
        data_fim = self.request.query_params.get('data_fim')
        etapa = self.request.query_params.get('etapa')
        
        if cliente_nome:
            queryset = queryset.filter(
                ctrl_cliente__enti_nome__icontains=cliente_nome
            )
        if vendedor_nome:
            queryset = queryset.filter(
                ctrl_vendedor__enti_nome__icontains=vendedor_nome
            )
        if data_inicio:
            queryset = queryset.filter(ctrl_data__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(ctrl_data__lte=data_fim)
        if etapa:
            queryset = queryset.filter(ctrl_etapa=etapa)
        
        # Debug: Verificar SQL gerada
        print(f"🔍 DEBUG SQL: {queryset.query}")
        print(f"📊 DEBUG: Total de registros no queryset final: {queryset.count()}")
        
        # Adicionar distinct() para evitar duplicatas
        queryset = queryset.distinct()
        print(f"📊 DEBUG: Total após distinct(): {queryset.count()}")
        
        return queryset.order_by('ctrl_numero')



    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            context['banco'] = get_licenca_db_config(self.request)
        except Exception:
            context['banco'] = 'default'
        
        # Pegar empresa_id do header X-Empresa (prioridade)
        empresa_id = self.request.headers.get("X-Empresa")
        
        # Fallback: pegar do usuário logado
        if not empresa_id and hasattr(self.request.user, 'empresa_id'):
            empresa_id = self.request.user.empresa_id
        
        # Fallback: pegar dos dados da requisição
        if not empresa_id and self.request.data.get('ctrl_empresa'):
            empresa_id = self.request.data.get('ctrl_empresa')
        
        if empresa_id:
            context['empresa_id'] = int(empresa_id)
        
        print(f"🔍 CONTEXTO EMPRESA_ID: {context.get('empresa_id')}")
        return context

    def destroy(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request)
        visita = self.get_object()
        
        try:
            visita.delete()
            logger.info(f"🗑️ Exclusão da visita ID {visita.ctrl_id} concluída")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Erro ao excluir visita: {e}")
            return Response(
                {"detail": "Erro ao excluir visita."},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'], url_path='estatisticas')
    def estatisticas(self, request, slug=None):
        """
        Endpoint para retornar estatísticas pré-calculadas das visitas
        """
        try:
            banco = get_licenca_db_config(request)
            if not banco:
                logger.error("Banco de dados não encontrado.")
                raise NotFound("Banco de dados não encontrado.")
            
            empresa_id = request.headers.get("X-Empresa")
            filial_id = request.headers.get("X-Filial")
            
            # Base queryset
            queryset = Controlevisita.objects.using(banco)
            
            # Aplicar filtros de empresa e filial
            if empresa_id:
                queryset = queryset.filter(ctrl_empresa=empresa_id)
            if filial_id:
                queryset = queryset.filter(ctrl_filial=filial_id)
            
            # Data atual para cálculos
            hoje = date.today()
            inicio_mes = hoje.replace(day=1)
            inicio_ano = hoje.replace(month=1, day=1)
            
            # Estatísticas gerais
            total_visitas = queryset.count()
            visitas_mes_atual = queryset.filter(ctrl_data__gte=inicio_mes).count()
            visitas_ano_atual = queryset.filter(ctrl_data__gte=inicio_ano).count()
            
            # Estatísticas por etapa
            # Na linha 142, substituir:
            # for etapa_id, etapa_nome in Controlevisita.ETAPA_CHOICES:
            
            # Por:
            etapas_stats = {}
            etapas = Etapavisita.objects.using(banco).all()
            if empresa_id:
                etapas = etapas.filter(etap_empr=empresa_id)
            
            for etapa in etapas:
                count = queryset.filter(ctrl_etapa=etapa.etap_id).count()
                etapas_stats[etapa.etap_descricao] = count
            
            # Visitas por vendedor (top 5)
            vendedores_stats = list(
                queryset.select_related('ctrl_vendedor')
                .values('ctrl_vendedor__enti_nome')
                .annotate(total=Count('ctrl_id'))
                .order_by('-total')[:5]
            )
            
            # Média de KM percorrido
            visitas_com_km = queryset.exclude(
                Q(ctrl_km_inic__isnull=True) | Q(ctrl_km_fina__isnull=True)
            )
            
            km_total = 0
            km_count = 0
            for visita in visitas_com_km:
                if visita.ctrl_km_inic and visita.ctrl_km_fina:
                    km_total += float(visita.ctrl_km_fina - visita.ctrl_km_inic)
                    km_count += 1
            
            km_medio = round(km_total / km_count, 2) if km_count > 0 else 0
            
            # Visitas dos últimos 7 dias
            sete_dias_atras = hoje - timedelta(days=7)
            visitas_ultimos_7_dias = queryset.filter(ctrl_data__gte=sete_dias_atras).count()
            
            # Próximas visitas agendadas
            proximas_visitas_count = queryset.filter(
                ctrl_prox_visi__gte=hoje
            ).count()
            
            estatisticas = {
                'total_visitas': total_visitas,
                'visitas_mes_atual': visitas_mes_atual,
                'visitas_ano_atual': visitas_ano_atual,
                'visitas_ultimos_7_dias': visitas_ultimos_7_dias,
                'proximas_visitas_agendadas': proximas_visitas_count,
                'km_medio_por_visita': km_medio,
                'etapas': etapas_stats,
                'top_vendedores': [
                    {
                        'vendedor': item['ctrl_vendedor__enti_nome'] or 'Sem vendedor',
                        'total_visitas': item['total']
                    }
                    for item in vendedores_stats
                ],
                'data_atualizacao': hoje.isoformat()
            }
            
            logger.info(f"📊 Estatísticas calculadas: {total_visitas} visitas processadas")
            return Response(estatisticas)
            
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas: {e}")
            return Response(
                {"detail": "Erro ao calcular estatísticas."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='proximas')
    def proximas_visitas(self, request, slug=None):
        """
        Endpoint para retornar lista das próximas visitas agendadas
        """
        try:
            banco = get_licenca_db_config(request)
            if not banco:
                logger.error("Banco de dados não encontrado.")
                raise NotFound("Banco de dados não encontrado.")
            
            empresa_id = request.headers.get("X-Empresa")
            filial_id = request.headers.get("X-Filial")
            
            # Data atual
            hoje = date.today()
            
            # Filtrar próximas visitas
            queryset = Controlevisita.objects.using(banco).select_related(
                'ctrl_cliente',
                'ctrl_vendedor',
                'ctrl_empresa'
            ).filter(
                ctrl_prox_visi__gte=hoje
            )
            
            # Aplicar filtros de empresa e filial
            if empresa_id:
                queryset = queryset.filter(ctrl_empresa=empresa_id)
            if filial_id:
                queryset = queryset.filter(ctrl_filial=filial_id)
            
            # Ordenar por data da próxima visita
            queryset = queryset.order_by('ctrl_prox_visi')
            limit = int(request.query_params.get('limit', 1000))
            queryset = queryset[:limit]
            
            # Serializar os dados
            proximas_visitas = []
            for visita in queryset:
                dias_restantes = (visita.ctrl_prox_visi - hoje).days
                
                proxima_visita = {
                    'ctrl_id': visita.ctrl_id,
                    'ctrl_numero': visita.ctrl_numero,
                    'ctrl_data_original': visita.ctrl_data.isoformat() if visita.ctrl_data else None,
                    'ctrl_prox_visi': visita.ctrl_prox_visi.isoformat(),
                    'dias_restantes': dias_restantes,
                    'cliente': {
                        'id': visita.ctrl_cliente.enti_clie if visita.ctrl_cliente else None,
                        'nome': visita.ctrl_cliente.enti_nome if visita.ctrl_cliente else 'Cliente não informado'
                    },
                    'vendedor': {
                        'id': visita.ctrl_vendedor.enti_clie if visita.ctrl_vendedor else None,
                        'nome': visita.ctrl_vendedor.enti_nome if visita.ctrl_vendedor else 'Vendedor não informado'
                    },
                    'etapa': {
                        'id': visita.ctrl_etapa.etap_id if visita.ctrl_etapa else None,
                        'nome': visita.ctrl_etapa.etap_descricao if visita.ctrl_etapa else 'Não informado'
                    },
                    'contato': visita.ctrl_contato,
                    'telefone': visita.ctrl_fone,
                    'observacoes': visita.ctrl_obse,
                    'urgencia': 'alta' if dias_restantes <= 3 else 'media' if dias_restantes <= 7 else 'baixa'
                }
                proximas_visitas.append(proxima_visita)
            
            resultado = {
                'total': len(proximas_visitas),
                'proximas_visitas': proximas_visitas,
                'data_consulta': hoje.isoformat()
            }
            
            logger.info(f"📅 Próximas visitas consultadas: {len(proximas_visitas)} encontradas")
            return Response(resultado)
            
        except Exception as e:
            logger.error(f"Erro ao buscar próximas visitas: {e}")
            return Response(
                {"detail": "Erro ao buscar próximas visitas."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ItensVisitaViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'Controle de Visitas'
    serializer_class = ItensVisitaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['item_empr', 'item_fili', 'item_visita', 'item_prod']
    
    def get_queryset(self):
        banco = self.get_banco()
        return ItensVisita.objects.using(banco).all().order_by('-item_data')
    
    @action(detail=False, methods=['post'], url_path='calcular-metragem-pisos')
    def calcular_metragem_pisos(self, request, slug=None):
        banco = self.get_banco()
        produto_id = request.data.get('produto_id')
        tamanho_m2 = request.data.get('tamanho_m2')
        percentual_quebra = request.data.get('percentual_quebra', 0)
        condicao = request.data.get('condicao', '0')

        # Log dos dados recebidos
        print(f"[calcular_metragem] Dados recebidos: {request.data}")
        print(f"[calcular_metragem] produto_id: {produto_id}, tamanho_m2: {tamanho_m2}, percentual_quebra: {percentual_quebra}")

        try:
            produto = Produtos.objects.using(banco).get(prod_codi=produto_id)
            print(f"[calcular_metragem] Produto encontrado: {produto.prod_nome}, m2_por_caixa: {getattr(produto, 'prod_cera_m2cx', None)}, pc_por_caixa: {getattr(produto, 'prod_cera_pccx', None)}")
        except Produtos.DoesNotExist:
            return Response({'error': 'Produto não encontrado'}, status=status.HTTP_404_NOT_FOUND)

        calculo = calcular_item(SimpleNamespace(
            item_m2=tamanho_m2,
            item_queb=percentual_quebra,
            item_unit=0,
        ), produto)

        print(f"[calcular_metragem] Resultado do cálculo: {calculo}")

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
        prod_pccx_attr = getattr(produto, "prod_cera_pccx", None)
        
        m2_por_caixa = parse_decimal(prod_m2cx_attr) if prod_m2cx_attr is not None else None
        pc_por_caixa = parse_decimal(prod_pccx_attr) if prod_pccx_attr is not None else None   
        
        unidade = str(produto.prod_unme).strip().upper() if produto.prod_unme else None
        if unidade in ["METRO QUADRADO", "M²", "M2", "M"]:
            unidade = "M2"
        elif unidade in ["PEÇA", "PÇ", "BARRA"]:
            unidade = "PC"
        
        resultado = {
            "produto_id": produto_id,
            "produto_nome": produto.prod_nome,
            "condicao_pagamento": "À Vista" if condicao == "0" else "A Prazo",
            "preco_unitario": preco_unitario,
            "valor_total": valor_total,
            "total": valor_total,
            "m2_por_caixa": m2_por_caixa,
            "pc_por_caixa": pc_por_caixa,
            "metragem_total": calculo.get("metragem_real"),
            "metragem_real": calculo.get("metragem_real"),
            "metragem_com_perda": calculo.get("metragem_com_perda"),
            "caixas_necessarias": calculo.get("caixas_necessarias"),
            "preco_origem": preco_origem,
            "unidade_medida": unidade,
        }
        
        print(f"[calcular_metragem] Resultado final: {resultado}")

        return Response(resultado)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    @action(detail=False, methods=['post'], url_path='exportar-para-orcamento')
    def exportar_para_orcamento(self, request, slug=None):
        """Exporta itens de uma visita para um novo orçamento (normal ou pisos)"""
        try:
            banco = get_licenca_db_config(request)
            serializer = ExportarVisitaParaOrcamentoSerializer(data=request.data, context={'banco': banco})
            
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            visita_id = serializer.validated_data['visita_id']
            
            # Buscar visita
            visita = Controlevisita.objects.using(banco).get(ctrl_id=visita_id)
            
            # Verificar se há itens com cálculo de pisos na visita
            tem_itens_pisos = ItensVisita.objects.using(banco).filter(
                item_visita=visita_id,
                item_tipo_calculo='pisos'
            ).exists()
            
            # Verificar se o módulo de Pisos está liberado
            tem_modulo_pisos = verificar_modulo_pisos_liberado(request)
            
            # Só gera orçamento de pisos se tiver itens de pisos E módulo liberado
            if tem_itens_pisos and tem_modulo_pisos:
                # Gerar orçamento de pisos
                orcamento = exportar_visita_para_orcamento_pisos(visita, banco, request)
                tipo_orcamento = "pisos"
                numero_orcamento = orcamento.orca_nume
                valor_total = orcamento.orca_tota
            else:
                # Gerar orçamento normal
                orcamento = exportar_visita_para_orcamento(visita, banco)
                tipo_orcamento = "normal"
                numero_orcamento = orcamento.pedi_nume
                valor_total = orcamento.pedi_tota
            
            return Response({
                'detail': f'Orçamento de {tipo_orcamento} criado com sucesso',
                'tipo_orcamento': tipo_orcamento,
                'orcamento_numero': numero_orcamento,
                'valor_total': valor_total
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erro ao exportar visita para orçamento: {e}")
            return Response(
                {'detail': 'Erro interno do servidor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EtapaVisitaViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
 
    serializer_class = EtapaVisitaSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['etap_empr', 'etap_nume']
    search_fields = ['etap_descricao', 'etap_obse']
    ordering_fields = ['etap_nume', 'etap_descricao']
    ordering = ['etap_nume']
    lookup_field = 'etap_id'
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")
        
        empresa_id = self.request.headers.get("X-Empresa")
        
        queryset = Etapavisita.objects.using(banco).select_related('etap_empr').all()
        
        if empresa_id:
            queryset = queryset.filter(etap_empr=empresa_id)
        
        return queryset.order_by('etap_nume')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def create(self, request, *args, **kwargs):
        print(f"🔍 VIEW - DADOS RECEBIDOS: {request.data}")
        print(f"🔍 VIEW - MÉTODO: {request.method}")
        print(f"🔍 VIEW - CONTENT TYPE: {request.content_type}")
        
        try:
            response = super().create(request, *args, **kwargs)
            print(f"✅ VIEW - SUCESSO: {response.status_code}")
            return response
        except Exception as e:
            print(f"🚨 VIEW - ERRO: {e}")
            print(f"🚨 VIEW - TIPO DO ERRO: {type(e)}")
            raise



        


    
    
