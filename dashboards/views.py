from rest_framework.views import APIView
from rest_framework.response import Response
from Produtos.models import SaldoProduto
from Pedidos.models import PedidoVenda
from rest_framework import status
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from core.middleware import get_licenca_slug
from .serializers import DashboardSerializer
from django.db.models import Sum, F
from decimal import Decimal

class DashboardAPIView(ModuloRequeridoMixin, APIView):
    modulo_necessario = 'Dashboard'
    def get(self, request, slug=None):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        # Top 10 produtos com mais saldo
        saldos = (
            SaldoProduto.objects.all()  # Remove o uso do db_alias
            .values(nome=F('produto_codigo__prod_nome'))
            .annotate(total=Sum('saldo_estoque'))
            .order_by('-total')[:10]
        )

        # Últimos 10 pedidos
        pedidos = (
            PedidoVenda.objects.all()  # Remove o uso do db_alias
            .order_by('-pedi_data')[:10]  # Substitua 'pedi_data' se seu campo for outro
            .values(
                cliente=F('pedi_forn__enti_nome'),
                total=F('pedi_tota'),
                data=F('pedi_data')  
            )
        )

        # Convertendo Decimal pra garantir compatibilidade com o serializer
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
