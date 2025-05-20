from xml.dom import ValidationErr
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
import re
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.http import Http404
from rest_framework.generics import ListAPIView
from django.db.models import Q, Subquery, OuterRef, DecimalField, Value as V, CharField
from django.db.models.functions import Coalesce, Cast
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from .models import Produtos, SaldoProduto, Tabelaprecos, UnidadeMedida
from .serializers import ProdutoSerializer, TabelaPrecoSerializer, UnidadeMedidaSerializer
from django_filters.rest_framework import DjangoFilterBackend


class UnidadeMedidaListView(ModuloRequeridoMixin, ListAPIView):
    modulo_necessario = 'Produtos'
    serializer_class = UnidadeMedidaSerializer
    def get(self, request, slug=None):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        banco = get_licenca_db_config(self.request)
        print(f"\n🔍 Banco de dados selecionado: {banco}")
        
        if banco:
            queryset = UnidadeMedida.objects.using(banco).all().order_by('unid_desc')
            print(f"📦 Total de unidades encontradas: {queryset.count()}")
            serializer = UnidadeMedidaSerializer(queryset, many=True)
            return Response(serializer.data)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context



class ProdutoListView(ModuloRequeridoMixin, APIView):
    modulo_necessario = 'Produtos'
    permission_classes = [IsAuthenticated]

    def get(self, request):
        banco = get_licenca_db_config(self.request)

        if not banco:
            return Response({"error": "Banco não encontrado."}, status=400)

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


    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
        
        
        
class ProdutoViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_necessario = 'Produtos'
    permission_classes = [IsAuthenticated]
    serializer_class = ProdutoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['prod_nome', 'prod_codi', 'prod_coba']
    filterset_fields = ['prod_empr']
    

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
    def busca(self, request, slug=None):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            banco = get_licenca_db_config(self.request)
            print(f"\n🔍 Banco de dados selecionado: {banco}")
            q = request.query_params.get("q", "")

            saldo_subquery = Subquery(
                SaldoProduto.objects.using(banco).filter(
                    produto_codigo=OuterRef('pk')
                ).values('saldo_estoque')[:1],
                output_field=DecimalField()
            )

            produtos = Produtos.objects.using(banco).annotate(
                saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField()),
                prod_coba_str=Coalesce(Cast('prod_coba', CharField()), V(''))
            ).filter(
                Q(prod_nome__icontains=q) |
                Q(prod_coba_str__icontains=q) |
                Q(prod_codi__icontains=q.lstrip("0"))  
            )


            serializer = self.get_serializer(produtos, many=True)
            return Response(serializer.data)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'detail': f'Erro interno: {str(e)}'}, status=500)

    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        serializer = self.get_serializer(data=request.data, context={'banco': banco})
        serializer.is_valid(raise_exception=True)
        
        produto = serializer.save()
        
        precos_data = request.data.get('precos', [])
        serializer.update_or_create_precos(produto, precos_data)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'banco': banco})
        serializer.is_valid(raise_exception=True)

        produto = serializer.save()

        precos_data = request.data.get('precos', [])
        serializer.update_or_create_precos(produto, precos_data)

        return Response(serializer.data)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context


class TabelaPrecoMobileViewSet(viewsets.ModelViewSet):
    serializer_class = TabelaPrecoSerializer
    lookup_field = 'lookup_key'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        return Tabelaprecos.objects.using(banco).all()

    def get_object(self):
        banco = get_licenca_db_config(self.request)
        slug = self.kwargs.get(self.lookup_field)
        if not slug:
            raise ValidationError("Chave composta não fornecida")

        try:
            tabe_empr, tabe_fili, tabe_prod = slug.split('-')
        except ValueError:
            raise ValidationError("Chave composta inválida")

        return get_object_or_404(
            Tabelaprecos.objects.using(banco),
            tabe_empr=tabe_empr,
            tabe_fili=tabe_fili,
            tabe_prod=tabe_prod,
        )

    def update(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False, context={'using': banco})
        serializer.is_valid(raise_exception=True)
        serializer.save()  # Remove o using daqui
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        data = request.data

        try:
            obj = Tabelaprecos.objects.using(banco).get(
                tabe_empr=data['tabe_empr'],
                tabe_fili=data['tabe_fili'],
                tabe_prod=data['tabe_prod']
            )
            serializer = self.get_serializer(obj, data=data, context={'using': banco})
        except Tabelaprecos.DoesNotExist:
            serializer = self.get_serializer(data=data, context={'using': banco})

        serializer.is_valid(raise_exception=True)
        serializer.save()  # Remove o using daqui
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['using'] = get_licenca_db_config(self.request)
        return context
