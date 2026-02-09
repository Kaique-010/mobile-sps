from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from core.decorator import ModuloRequeridoMixin
from core.registry import get_licenca_db_config

from ..models import Produtos, Tabelaprecos
from ..serializers.produto_serializer import ProdutoSerializer, ProdutoServicoSerializer
from ..serializers.tabela_preco_serializer import TabelaPrecoSerializer
from ..consultas.produto_consultas import listar_produtos, buscar_produto_por_codigo
from ..servicos.produto_servico import buscar_produto_por_hash
from ..servicos.etiqueta_servico import gerar_dados_etiquetas
from ..servicos.preco_servico import atualizar_preco_com_historico, criar_preco_com_historico

class ProdutoListView(ModuloRequeridoMixin, APIView):
    """
    View para listagem otimizada de produtos com saldo e preços.
    """
    modulo_necessario = 'Produtos'

    def get(self, request):
        banco = get_licenca_db_config(request)
        
        # Filtros
        q = request.query_params.get('q')
        marca_nome = request.query_params.get('marca')
        saldo_filter = request.query_params.get('saldo')
        limit = int(request.query_params.get('limit', 50))
        
        # Parâmetros de contexto
        empresa_id = request.headers.get('X-Empresa') or request.session.get('empresa_id')
        filial_id = request.headers.get('X-Filial') or request.session.get('filial_id')

        queryset = listar_produtos(
            banco=banco,
            empresa_id=empresa_id,
            filial_id=filial_id,
            q=q,
            marca_nome=marca_nome,
            saldo_filter=saldo_filter,
            limit=limit
        )

        serializer = ProdutoSerializer(queryset, many=True, context={'banco': banco})
        return Response(serializer.data)


class ProdutoViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_necessario = 'Produtos'
    serializer_class = ProdutoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['prod_nome', 'prod_codi', 'prod_coba']
    filterset_fields = ['prod_empr']

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        
        empresa_id = (
            self.request.query_params.get('prod_empr') or 
            self.request.headers.get('X-Empresa') or 
            self.request.session.get('empresa_id') or
            self.request.headers.get('Empresa_id')
        )

        filial_id = (
            self.request.query_params.get('prod_fili') or
            self.request.headers.get('X-Filial') or 
            self.request.session.get('filial_id') or
            self.request.headers.get('Filial_id')
        )
        
        # Reutiliza a consulta otimizada, mas sem limite padrão do ListView
        return listar_produtos(
            banco=banco,
            empresa_id=empresa_id,
            filial_id=filial_id
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    @action(detail=False, methods=['get'])
    def busca(self, request, slug=None):
        banco = get_licenca_db_config(request)
        empresa_id = (
            request.query_params.get('empresa') or 
            request.headers.get('X-Empresa') or 
            request.session.get('empresa_id') or
            request.headers.get('Empresa_id')
        )
        
        # 1. Busca por Hash (QR Code)
        hash_busca = request.query_params.get('hash')
        if hash_busca:
            cod_produto = buscar_produto_por_hash(banco, hash_busca, empresa_id)
            if cod_produto:
                produto = buscar_produto_por_codigo(banco, empresa_id, cod_produto)
                if produto:
                    serializer = self.get_serializer(produto)
                    return Response(serializer.data)
            return Response({"detail": "Produto não encontrado via hash"}, status=status.HTTP_404_NOT_FOUND)

        # 2. Busca convencional
        termo = request.query_params.get('q') or request.query_params.get('termo')
        
        # Lógica de fallback para leitura de QR Code direto no campo de busca
        if termo and "/p/" in termo:
            try:
                # Extrai o hash da URL (ex: https://mobile-sps.site/p/HASH)
                parts = termo.split("/p/")
                if len(parts) > 1:
                    hash_extraido = parts[1].strip().split("/")[0].split("?")[0].split("#")[0]
                    
                    cod_produto = buscar_produto_por_hash(banco, hash_extraido, empresa_id)
                    if cod_produto:
                        termo = cod_produto
            except Exception:
                pass

        if not termo:
            return Response([])

        queryset = listar_produtos(
            banco=banco,
            empresa_id=empresa_id,
            q=termo,
            limit=100
        )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def impressao_etiquetas(self, request):
        banco = get_licenca_db_config(request)
        empresa_id = request.data.get('empresa_id')
        produtos_ids = request.data.get('produtos', [])

        if not empresa_id or not produtos_ids:
            return Response(
                {"error": "Empresa e lista de produtos são obrigatórios"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        etiquetas = gerar_dados_etiquetas(banco, empresa_id, produtos_ids)
        return Response(etiquetas)

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
        
        # Preparar dados
        dados_preco = request.data.copy()
        
        try:
            preco_existente = Tabelaprecos.objects.using(banco).get(
                tabe_prod=produto.prod_codi,
                tabe_empr=produto.prod_empr,
                tabe_fili=dados_preco.get('tabe_fili', 1)
            )
            
            # Remover campos que não devem ser atualizados diretamente se não fornecidos
            campos_validos = [f.name for f in Tabelaprecos._meta.fields]
            dados_limpos = {k: v for k, v in dados_preco.items() if k in campos_validos}
            
            atualizar_preco_com_historico(banco, preco_existente, dados_limpos)
            serializer = TabelaPrecoSerializer(preco_existente, context={'banco': banco})
            return Response(serializer.data)
            
        except Tabelaprecos.DoesNotExist:
            dados_preco['tabe_prod'] = produto.prod_codi
            dados_preco['tabe_empr'] = produto.prod_empr
            dados_preco['tabe_fili'] = dados_preco.get('tabe_fili', 1)
            
            # Remover campos inválidos
            campos_validos = [f.name for f in Tabelaprecos._meta.fields]
            dados_limpos = {k: v for k, v in dados_preco.items() if k in campos_validos}
            
            novo_preco = criar_preco_com_historico(banco, dados_limpos)
            serializer = TabelaPrecoSerializer(novo_preco, context={'banco': banco})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def cadastro_servico(self, request):
        """
        Endpoint específico para cadastro simplificado de serviços/produtos.
        """
        banco = get_licenca_db_config(request)
        serializer = ProdutoServicoSerializer(data=request.data, context={'banco': banco})
        
        if serializer.is_valid():
            produto = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        precos_data = request.data.pop('precos', None)
        
        serializer = self.get_serializer(
            data=request.data, 
            context={'banco': banco}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Se houver dados de preço, criar
        if precos_data and serializer.instance:
            precos_data['tabe_prod'] = serializer.instance.prod_codi
            precos_data['tabe_empr'] = serializer.instance.prod_empr
            precos_data['tabe_fili'] = 1 # Padrão
            criar_preco_com_historico(banco, precos_data)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        instance = self.get_object()
        precos_data = request.data.pop('precos', None)

        # Atualizar produto
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=kwargs.pop('partial', False),
            context={'banco': banco}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Atualizar preço se fornecido
        if precos_data:
            try:
                preco = Tabelaprecos.objects.using(banco).get(
                    tabe_prod=instance.prod_codi,
                    tabe_empr=instance.prod_empr,
                    tabe_fili=1
                )
                atualizar_preco_com_historico(banco, preco, precos_data)
            except Tabelaprecos.DoesNotExist:
                precos_data['tabe_prod'] = instance.prod_codi
                precos_data['tabe_empr'] = instance.prod_empr
                precos_data['tabe_fili'] = 1
                criar_preco_com_historico(banco, precos_data)

        return Response(serializer.data)
