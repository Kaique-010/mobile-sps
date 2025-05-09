from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from django.db.models import Q, Subquery, OuterRef, DecimalField, Value as V, CharField
from django.db.models.functions import Coalesce, Cast
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from .models import Produtos, SaldoProduto, UnidadeMedida
from .serializers import ProdutoSerializer, UnidadeMedidaSerializer


class UnidadeMedidaListView(ListAPIView):
    queryset = UnidadeMedida.objects.all()
    serializer_class = UnidadeMedidaSerializer

class ProdutoListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        db_alias = getattr(request, 'db_alias', 'default')

        saldo_subquery = Subquery(
            SaldoProduto.objects.using(db_alias).filter(
                produto_codigo=OuterRef('pk')
            ).values('saldo_estoque')[:1],
            output_field=DecimalField()
        )

        queryset = Produtos.objects.using(db_alias).annotate(
            saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField())
        )

        serializer = ProdutoSerializer(queryset, many=True)
        return Response(serializer.data)


class ProdutoViewSet(viewsets.ModelViewSet):
    serializer_class = ProdutoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['prod_nome', 'prod_codi', 'prod_coba']

    def get_queryset(self):
        db_alias = getattr(self.request, 'db_alias', 'default')

        saldo_subquery = Subquery(
            SaldoProduto.objects.using(db_alias).filter(
                produto_codigo=OuterRef('pk')
            ).values('saldo_estoque')[:1],
            output_field=DecimalField()
        )

        return Produtos.objects.using(db_alias).annotate(
            saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField())
        )

    @action(detail=False, methods=["get"])
    def busca(self, request):
        db_alias = getattr(request, 'db_alias', 'default')
        q = request.query_params.get("q", "").lstrip("0") 
        saldo_subquery = Subquery(
            SaldoProduto.objects.using(db_alias).filter(
                produto_codigo=OuterRef('pk')
            ).values('saldo_estoque')[:1],
            output_field=DecimalField()
        )

        produtos = Produtos.objects.using(db_alias).annotate(
            saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField()),
            prod_coba_str=Cast('prod_coba', CharField())
        ).filter(
            Q(prod_nome__icontains=q) |
            Q(prod_coba_str__icontains=q) |
            Q(prod_codi__icontains=q)
        )

        serializer = self.get_serializer(produtos, many=True)
        return Response(serializer.data)

