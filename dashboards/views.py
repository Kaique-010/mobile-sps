from rest_framework.views import APIView
from rest_framework.response import Response
from Produtos.models import SaldoProduto
from Pedidos.models import PedidoVenda
from .serializers import DashboardSerializer
from django.db.models import Sum, F
from decimal import Decimal

class DashboardAPIView(APIView):
    def get(self, request):
        db_alias = getattr(request, 'db_alias', 'default')

        saldos = SaldoProduto.objects.using(db_alias).values(
            nome=F('produto_codigo__prod_nome')
        ).annotate(
            total=Sum('saldo_estoque')
        )

        pedidos = PedidoVenda.objects.using(db_alias).values(
            cliente=F('pedi_forn__enti_nome')
        ).annotate(
            total=Sum('pedi_tota')
        )

        # Convertendo Decimal pra float porque o serializer espera DecimalField
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
