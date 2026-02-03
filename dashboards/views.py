from decimal import Decimal, InvalidOperation
from datetime import datetime, time
from re import S
from typing import Annotated
from rest_framework.views import APIView
from rest_framework.response import Response
from Entidades.models import Entidades
from Entradas_Estoque.models import EntradaEstoque
from Licencas.models import Usuarios
from Produtos.models import Produtos, ProdutosDetalhados, SaldoProduto
from Pedidos.models import Itenspedidovenda, PedidoVenda
from OrdemdeServico.models import OrdensEletro
from rest_framework import status
from Saidas_Estoque.models import SaidasEstoque
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from core.middleware import get_licenca_slug
from .serializers import DashboardSerializer
from django.db.models import Sum, F, OuterRef, Subquery, Max, Count
from django.db.models.functions import Cast
from django.db.models import BigIntegerField
from decimal import Decimal
from datetime import datetime
from .utils import enviar_email, enviar_whatsapp
from core.mixins.ususario_com_setor import UsuarioComSetorMixin

import logging

logger = logging.getLogger(__name__)


def safe_decimal(value):
    if value is None:
        return Decimal(0)
    try:
        d = Decimal(str(value))
        if d.is_nan() or d.is_infinite():
            return Decimal(0)
        return d
    except (TypeError, ValueError, InvalidOperation):
        return Decimal(0)


def resolve_dashboard_mode(ctx):
    if not ctx['is_banco_144']:
        return 'default'
    if ctx['tem_setor']:
        return 'os_por_setor'
    return 'home_eletro'


class DashboardAPIView(UsuarioComSetorMixin, APIView):
    def get(self, request, slug=None):
        slug = get_licenca_slug()
        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        
        data = {}
        empresa = request.query_params.get('empresa_id') or request.query_params.get('empresa')
        filial = request.query_params.get('filial_id') or request.query_params.get('filial')
        
        if not empresa:
             empresa = (request.headers.get('Empresa') or 
                        request.headers.get('empresaId') or 
                        request.headers.get('empresa_id') or 
                        request.headers.get('X-Empresa')) 
                        
        if not filial:
             filial = (request.headers.get('Filial') or 
                       request.headers.get('filialId') or 
                       request.headers.get('filial_id') or 
                       request.headers.get('X-Filial'))
        
        ctx = request.licenca_ctx
        dashboard_mode = resolve_dashboard_mode(ctx)
        
        # Monta filtros base
        filtros_base = {}
        if empresa:
            filtros_base['empresa'] = empresa
        if filial:
            filtros_base['filial'] = filial
        
        # Monta dados com base no dashboard_mode
        if dashboard_mode == 'default':
            filtros_pedidos = {}
            if empresa:
                filtros_pedidos['pedi_empr'] = empresa
            if filial:
                filtros_pedidos['pedi_fili'] = filial

            saldos = (
                SaldoProduto.objects.filter(**filtros_base)
                .values(nome=F('produto_codigo__prod_nome'))
                .annotate(total=Sum('saldo_estoque'))
                .order_by('-total')[:10]
            )

            cliente_nome = Entidades.objects.filter(
                enti_clie=Cast(OuterRef('pedi_forn'), BigIntegerField())
            ).values('enti_nome')[:1]

            pedidos_query = PedidoVenda.objects.filter(**filtros_pedidos)
            
            pedidos = (
                pedidos_query.annotate(
                    cliente_nome=Subquery(cliente_nome)
                )
                .values('cliente_nome')
                .annotate(
                    total=Sum('pedi_tota'),
                    data=Max('pedi_data')
                )
                .order_by('-total')[:10] 
                .values(
                    cliente=F('cliente_nome'),
                    total=F('total'),
                    data=F('data')
                )
            )

            for item in saldos:
                item['total'] = safe_decimal(item['total'])

            for item in pedidos:
                item['total'] = safe_decimal(item['total'])

            data['saldos_produto'] = saldos
            data['pedidos_por_cliente'] = pedidos

            
        elif dashboard_mode == 'home_eletro':
            agrupado = (
                ProdutosDetalhados.objects.using(slug)
                .filter(**filtros_base)
                .filter(saldo__gt=0)
                .values('marca_nome')
                .annotate(
                    total_custo=Sum('valor_total_estoque'),
                    total_estoque=Sum('valor_total_estoque')
                )
                .order_by('-marca_nome')
            )

            # Processamento em memória
            dados_agrupados = list(agrupado)
            
            total_valor_estoque = Decimal(0)
            produto_sem_marca = Decimal(0)
            produto_sem_estoque = Decimal(0)
            lista_marcas_validas = []

            for item in dados_agrupados:
                estoque = safe_decimal(item['total_estoque'])
                custo = safe_decimal(item['total_custo'])
                
                total_valor_estoque += estoque
                
                if item['marca_nome'] is None:
                    produto_sem_marca += estoque
                elif estoque == 0:
                    produto_sem_estoque += custo
                else:
                    lista_marcas_validas.append({
                        'marca_nome': item['marca_nome'],
                        'total': custo
                    })
            
            top10_marcas = lista_marcas_validas[:10]

            if produto_sem_marca > 0:
                top10_marcas.append({
                    'marca_nome': 'Sem Marca',
                    'total': produto_sem_marca
                })

            data['produto_sem_marca'] = produto_sem_marca
            data['produto_sem_estoque'] = produto_sem_estoque
            data['ordens_eletro'] = top10_marcas
            data['total_valor_estoque'] = total_valor_estoque
            
           
        elif dashboard_mode == 'os_por_setor':
            status_permitidos = [
                "Aberta", 
                "Em Orçamento gerado", 
                "Aguardando Liberação", 
                "Liberada", 
                "Reprovada",
                "Atrasada"
            ]
            
            ordens_query = OrdensEletro.objects.using(slug).filter(**filtros_base)
            
            data['ordens_por_setor'] = (
                ordens_query
                .filter(setor=int(ctx['setor_id']))
                .filter(status_orde__in=status_permitidos)
                .values(
                    'nome_cliente',
                    ordem=F('ordem_de_servico'),
                    setor_nome_view=F('setor_nome'),
                    status=F('status_orde'),
                    data=F('data_abertura')
                )
                .order_by('-data')[:100]
            )
            
        serializer = DashboardSerializer(data)
        return Response(serializer.data)


class DashboardEstoqueView(APIView):
    def get(self, request, slug = None ):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        data_ini = request.query_params.get('data_ini')
        data_fim = request.query_params.get('data_fim')

        data_ini = datetime.strptime(data_ini, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()

        entradas = EntradaEstoque.objects.using(slug).filter(
            entr_data__range=(data_ini, data_fim)
        ).aggregate(
            total_quan=Sum('entr_quan'),
            total_valor=Sum('entr_tota')
        )

        saidas = SaidasEstoque.objects.using(slug).filter(
            said_data__range=(data_ini, data_fim)
        ).aggregate(
            total_quan=Sum('said_quan'),
            total_valor=Sum('said_tota')
        )

        top_produtos_saida = SaidasEstoque.objects.using(slug).filter(
            said_data__range=(data_ini, data_fim)
        ).values('said_prod').annotate(
            total=Sum('said_quan')
        ).order_by('-total')[:9]

        saldo_produtos = SaldoProduto.objects.using(slug).annotate(
            codigo=F('produto_codigo__prod_codi'),
            nome=F('produto_codigo__prod_nome')
        ).values('codigo', 'nome', 'saldo_estoque').order_by('-saldo_estoque')[:10]

        return Response({
            'entradas_periodo': entradas,
            'saidas_periodo': saidas,
            'top_produtos_saida': list(top_produtos_saida),
            'saldos_estoque': list(saldo_produtos)
        })


class DashboardVendasView(APIView):
    def get(self, request, slug=None):
        try:
            slug = get_licenca_slug()
            logger.debug(f"DashboardVendasView slug: {slug}")

            if not slug:
                logger.warning("Licença não encontrada no DashboardVendasView")
                return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

            data_ini = request.query_params.get('data_ini')
            data_fim = request.query_params.get('data_fim')
            logger.debug(f"Data_ini: {data_ini}, Data_fim: {data_fim}")

            data_ini = datetime.strptime(data_ini, '%Y-%m-%d')
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d')
            data_fim = datetime.combine(data_fim.date(), time.max)


            pedidos_periodo = PedidoVenda.objects.using(slug).filter(pedi_data__range=(data_ini, data_fim))
            logger.debug(f"Pedidos no período: {pedidos_periodo.count()}")

            total_pedidos = pedidos_periodo.count()
            total_faturado = pedidos_periodo.aggregate(Sum('pedi_tota'))['pedi_tota__sum'] or 0
            ticket_medio = total_faturado / total_pedidos if total_pedidos else 0
            logger.debug(f"Total faturado: {total_faturado}, Ticket médio: {ticket_medio}")

            top_vendas = Itenspedidovenda.objects.using(slug).filter(
                iped_data__range=(data_ini, data_fim)
            ).values('iped_prod').annotate(
                total=Sum('iped_quan')
            ).order_by('-total')[:10]
            logger.debug(f"Top vendas: {list(top_vendas)}")

            return Response({
                'total_pedidos': total_pedidos,
                'total_faturado': total_faturado,
                'ticket_medio': round(ticket_medio, 2),
                'top_vendas': list(top_vendas),
            })

        except Exception:
            logger.exception("Erro ao gerar dashboard de vendas")
            return Response({"erro": "Erro interno no servidor."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
    

class EnviarEmail(APIView):
    def post(self, request, slug = None ):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        
        email = request.data.get('email')
        dados = request.data.get('dados')
        
        if not email or not dados:
            return Response({'erro': 'Email e dados são obrigatórios'}, status= 400)
        
        enviado = enviar_email(email, dados)
        
        if enviado:
            return Response({'mensagem': 'E-mail enviado com sucesso'})
        return Response({'erro': 'Falha ao enviar o e-mail.'}, status=500)


class EnviarWhats(APIView):
    def post(self, request, slug = None ):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        numero = request.data.get('numero')
        dados = request.data.get('dados')
        
        if not numero or not  dados:
            return Response({'erro': 'numero e dados são obrigatórios'}, status= 400)
        
        enviado = enviar_whatsapp(numero, dados)
        
        if enviado:
            return Response({'mensagem': 'Whats enviado com sucesso'})
        return Response({'erro': 'Falha ao enviar o e-mail.'}, status=500)