from rest_framework.views import APIView
from django.db.models import Q
from rest_framework.decorators import action
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

    @action(detail=False, methods=["get"])
    def busca(self, request):
        q = request.query_params.get("q", "")
        saldo_subquery = Subquery(
            SaldoProduto.objects.filter(
                produto_codigo=OuterRef('pk')
            ).values('saldo_estoque')[:1],
            output_field=DecimalField()
        )

        produtos = Produtos.objects.annotate(
            saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField())
        ).filter(
            Q(prod_nome__icontains=q) | Q(prod_codi__icontains=q)
        )

        serializer = self.get_serializer(produtos, many=True)
        return Response(serializer.data)