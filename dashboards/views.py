from decimal import Decimal
from datetime import datetime, time
from typing import Annotated
from rest_framework.views import APIView
from rest_framework.response import Response
from Entidades.models import Entidades
from Entradas_Estoque.models import EntradaEstoque
from Produtos.models import Produtos, SaldoProduto
from Pedidos.models import Itenspedidovenda, PedidoVenda
from rest_framework import status
from Saidas_Estoque.models import SaidasEstoque
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from core.middleware import get_licenca_slug
from .serializers import DashboardSerializer
from django.db.models import Sum, F, OuterRef, Subquery, Max, Count
from decimal import Decimal
from datetime import datetime
from .utils import enviar_email, enviar_whatsapp

import logging

logger = logging.getLogger(__name__)

class DashboardAPIView(ModuloRequeridoMixin, APIView):
    modulo_necessario = 'dashboard'
    def get(self, request, slug=None):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        
        saldos = (
            SaldoProduto.objects.all()  
            .values(nome=F('produto_codigo__prod_nome'))
            .annotate(total=Sum('saldo_estoque'))
            .order_by('-total')[:10]
        )

        cliente_nome = Entidades.objects.filter(
            enti_clie=OuterRef('pedi_forn')
        ).values('enti_nome')[:1]

        pedidos = (
            PedidoVenda.objects.annotate(
                cliente_nome=Subquery(cliente_nome)
            )
            .values('cliente_nome')  # agrupa por cliente
            .annotate(
                total=Sum('pedi_tota'),
                data=Max('pedi_data')  # opcional: data do último pedido
            )
            .order_by('-total')[:10]  # top 10 clientes
            .values(
                cliente=F('cliente_nome'),
                total=F('total'),
                data=F('data')
            )
        )

        for item in saldos:
            item['total'] = Decimal(item['total']) if not isinstance(item['total'], Decimal) else item['total']
        for item in pedidos:
            item['total'] = Decimal(item['total']) if not isinstance(item['total'], Decimal) else item['total']

        data = {
            'saldos_produto': saldos,
            'pedidos_por_cliente': pedidos
        }

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