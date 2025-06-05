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
        
        preco_vista_subquery = Subquery(
            Tabelaprecos.objects.using(banco).filter(
                tabe_prod=OuterRef('prod_codi'),
                tabe_empr=OuterRef('prod_empr')
            ).values('tabe_avis')[:1],
            output_field=DecimalField()
        )

        preco_normal_subquery = Subquery(
            Tabelaprecos.objects.using(banco).filter(
                tabe_prod=OuterRef('prod_codi'),
                tabe_empr=OuterRef('prod_empr')
            ).values('tabe_prco')[:1],
            output_field=DecimalField()
        )

        return Produtos.objects.using(banco).annotate(
            saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField()),
            prod_preco_vista=Coalesce(preco_vista_subquery, V(0), output_field=DecimalField()),
            prod_preco_normal=Coalesce(preco_normal_subquery, V(0), output_field=DecimalField())
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
                prod_coba_str=Coalesce(Cast('prod_coba', CharField()), V('')),
                
            ).filter(
                Q(prod_nome__icontains=q) |
                Q(prod_coba_str__icontains=q) |
                Q(prod_codi__icontains=q.lstrip("0"))  
            )
            prod_preco_vista=Subquery(
            Tabelaprecos.objects.filter(tabe_prod=OuterRef('prod_codi'))
            .values('tabe_avis')[:1]
        )


            serializer = self.get_serializer(produtos, many=True)
            return Response(serializer.data)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'detail': f'Erro interno: {str(e)}'}, status=500)

    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        precos_data = request.data.pop('precos', None)
        
        serializer = self.get_serializer(
            data=request.data, 
            context={'banco': banco, 'precos_data': precos_data}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        precos_data = request.data.pop('precos', None)
        
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
            context={'banco': banco, 'precos_data': precos_data}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    @action(detail=True, methods=['get'])
    def precos(self, request, pk=None):
        produto = self.get_object()
        banco = get_licenca_db_config(request)
        
        precos = Tabelaprecos.objects.using(banco).filter(
            tabe_prod=produto.prod_codi,
            tabe_empr=produto.prod_empr
        )
        
        serializer = TabelaPrecoSerializer(precos, many=True, context={'banco': banco})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def atualizar_precos(self, request, pk=None):
        produto = self.get_object()
        banco = get_licenca_db_config(request)
        
        serializer = TabelaPrecoSerializer(
            data=request.data,
            context={'banco': banco}
        )
        
        if serializer.is_valid():
            try:
                preco = Tabelaprecos.objects.using(banco).get(
                    tabe_prod=produto.prod_codi,
                    tabe_empr=produto.prod_empr,
                    tabe_fili=request.data.get('tabe_fili', 1)
                )
                serializer.update(preco, serializer.validated_data)
            except Tabelaprecos.DoesNotExist:
                serializer.save(
                    tabe_prod=produto.prod_codi,
                    tabe_empr=produto.prod_empr,
                    tabe_fili=request.data.get('tabe_fili', 1)
                )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TabelaPrecoMobileViewSet(viewsets.ModelViewSet):
    serializer_class = TabelaPrecoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['tabe_empr', 'tabe_fili', 'tabe_prod']
    search_fields = ['tabe_prod']
    lookup_field = 'chave_composta'
    lookup_value_regex = '[^/]+'

    def get_object(self):
        # Extrair os componentes da chave composta
        chave = self.kwargs['chave_composta'].split('-')
        if len(chave) != 3:
            raise ValidationError("Formato de chave inválido")
        
        empresa, filial, produto = chave
        
        # Buscar o objeto
        queryset = self.get_queryset().filter(
            tabe_empr=empresa,
            tabe_fili=filial,
            tabe_prod=produto
        )
        
        obj = get_object_or_404(queryset)
        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Tabelaprecos.objects.none()
        
        queryset = Tabelaprecos.objects.using(banco)
        
        # Filtrar por empresa se fornecido
        empresa = self.request.query_params.get('empresa')
        if empresa:
            queryset = queryset.filter(tabe_empr=empresa)
            
        # Filtrar por filial se fornecido
        filial = self.request.query_params.get('filial')
        if filial:
            queryset = queryset.filter(tabe_fili=filial)
            
        # Filtrar por produto se fornecido
        produto = self.request.query_params.get('produto')
        if produto:
            queryset = queryset.filter(tabe_prod=produto)
            
        return queryset

    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response(
                {"detail": "Banco de dados não especificado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data, context={'banco': banco})
        serializer.is_valid(raise_exception=True)
        
        try:
            # Tentar encontrar registro existente
            preco = Tabelaprecos.objects.using(banco).get(
                tabe_empr=request.data['tabe_empr'],
                tabe_fili=request.data['tabe_fili'],
                tabe_prod=request.data['tabe_prod']
            )
            # Atualizar registro existente
            serializer.update(preco, serializer.validated_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Tabelaprecos.DoesNotExist:
            # Criar novo registro
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response(
                {"detail": "Banco de dados não especificado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
            context={'banco': banco}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
