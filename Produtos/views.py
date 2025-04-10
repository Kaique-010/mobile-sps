from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Subquery, OuterRef
from django.db.models import OuterRef, Subquery, DecimalField, Value as V
from django.db.models.functions import Coalesce
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from .models import Produtos, SaldoProduto
from .serializers import ProdutoSerializer

class ProdutoListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        saldo_subquery = Subquery(
            SaldoProduto.objects.filter(
                produto_codigo=OuterRef('pk')
            ).values('saldo_estoque')[:1],
            output_field=DecimalField()
        )

        queryset = Produtos.objects.annotate(
            saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField())
        )

        serializer = ProdutoSerializer(queryset, many=True)
        return Response(serializer.data)



class ProdutoViewSet(viewsets.ModelViewSet):
    serializer_class = ProdutoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['prod_nome', 'prod_codi']

    def get_queryset(self):
        saldo_subquery = Subquery(
            SaldoProduto.objects.filter(
                produto_codigo=OuterRef('pk')
            ).values('saldo_estoque')[:1],
            output_field=DecimalField()
        )

        return Produtos.objects.annotate(
            saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField())
        )