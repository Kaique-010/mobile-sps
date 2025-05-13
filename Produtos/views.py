from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from django.db.models import Q, Subquery, OuterRef, DecimalField, Value as V, CharField
from django.db.models.functions import Coalesce, Cast
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from core.registry import get_licenca_db_config
from .models import Produtos, SaldoProduto, UnidadeMedida
from .serializers import ProdutoSerializer, UnidadeMedidaSerializer


class UnidadeMedidaListView(ModuloRequeridoMixin, ListAPIView):
    modulo_necessario = 'Produtos'
    serializer_class = UnidadeMedidaSerializer
    def get(self, request):
        banco = get_licenca_db_config(self.request)
        print(f"\n🔍 Banco de dados selecionado: {banco}")
        
        if banco:
            queryset = UnidadeMedida.objects.using(banco).all().order_by('unid_desc')
            print(f"📦 Total de unidades encontradas: {queryset.count()}")
            serializer = UnidadeMedidaSerializer(queryset, many=True)
            return Response(serializer.data)
    

class ProdutoListView(ModuloRequeridoMixin, APIView):
    modulo_necessario = 'Produtos'
    permission_classes = [IsAuthenticated]

    def get(self, request):
        banco = get_licenca_db_config(self.request)
        print(f"\n🔍 Banco de dados selecionado: {banco}")
        
        if banco:
            queryset = Produtos.objects.using(banco).all().order_by('enti_nome')
            print(f"📦 Total de entidades encontradas: {queryset.count()}")
            serializer = ProdutoSerializer(queryset, many=True)
            return Response(serializer.data)

        saldo_subquery = Subquery(
            SaldoProduto.objects.using(banco).filter(
                produto_codigo=OuterRef('pk')
            ).values('saldo_estoque')[:1],
            output_field=DecimalField()
        )

        queryset = Produtos.objects.using(banco).annotate(
            saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField())
        )

        serializer = ProdutoSerializer(queryset, many=True)
        return Response(serializer.data)


class ProdutoViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_necessario = 'Produtos'
    permission_classes = [IsAuthenticated]
    serializer_class = ProdutoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['prod_nome', 'prod_codi', 'prod_coba']

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        print(f"\n🔍 Banco de dados selecionado: {banco}")

        saldo_subquery = Subquery(
            SaldoProduto.objects.using(banco).filter(
                produto_codigo=OuterRef('pk')
            ).values('saldo_estoque')[:1],
            output_field=DecimalField()
        )

        return Produtos.objects.using(banco).annotate(
            saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField())
        )

    @action(detail=False, methods=["get"])
    def busca(self, request):
        banco = get_licenca_db_config(self.request)
        print(f"\n🔍 Banco de dados selecionado: {banco}")
        q = request.query_params.get("q", "").lstrip("0") 
        saldo_subquery = Subquery(
            SaldoProduto.objects.using(banco).filter(
                produto_codigo=OuterRef('pk')
            ).values('saldo_estoque')[:1],
            output_field=DecimalField()
        )

        produtos = Produtos.objects.using(banco).annotate(
            saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField()),
            prod_coba_str=Cast('prod_coba', CharField())
        ).filter(
            Q(prod_nome__icontains=q) |
            Q(prod_coba_str__icontains=q) |
            Q(prod_codi__icontains=q)
        )

        serializer = self.get_serializer(produtos, many=True)
        return Response(serializer.data)

