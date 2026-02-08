from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from core.registry import get_licenca_db_config
from ..models import Tabelaprecos
from ..serializers.tabela_preco_serializer import TabelaPrecoSerializer
from ..servicos.preco_servico import criar_preco_com_historico, atualizar_preco_com_historico

class TabelaPrecoMobileViewSet(viewsets.ModelViewSet):
    serializer_class = TabelaPrecoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['tabe_empr', 'tabe_fili', 'tabe_prod']
    search_fields = ['tabe_prod']
    lookup_field = 'chave_composta'
    lookup_value_regex = '[^/]+'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Tabelaprecos.objects.none()
        
        queryset = Tabelaprecos.objects.using(banco)
        
        # Filtros adicionais manuais se necessário (além do filterset_fields)
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

        # Processar percentuais
        dados = request.data.copy()
        if 'percentual_avis' in dados and 'tabe_prco' in dados:
            preco_base = float(dados['tabe_prco'])
            percentual = float(dados.pop('percentual_avis'))
            dados['tabe_avis'] = round(preco_base * (1 + percentual / 100), 2)

        if 'percentual_apra' in dados and 'tabe_prco' in dados:
            preco_base = float(dados['tabe_prco'])
            percentual = float(dados.pop('percentual_apra'))
            dados['tabe_apra'] = round(preco_base * (1 + percentual / 100), 2)

        # Remover campos que não são do modelo
        campos_validos = [f.name for f in Tabelaprecos._meta.fields]
        dados_limpos = {k: v for k, v in dados.items() if k in campos_validos}

        instance = criar_preco_com_historico(banco, dados_limpos)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_object(self):
        # Extrair os componentes da chave composta
        chave = self.kwargs['chave_composta'].split('-')
        if len(chave) != 3:
            raise ValidationError("Formato de chave inválido")
        
        empresa, filial, produto = chave
        
        queryset = self.get_queryset().filter(
            tabe_empr=empresa,
            tabe_fili=filial,
            tabe_prod=produto
        )
        
        obj = get_object_or_404(queryset)
        self.check_object_permissions(self.request, obj)
        return obj

    def update(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response(
                {"detail": "Banco de dados não especificado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance = self.get_object()
        dados = request.data.copy()

        # Processar percentuais
        if 'percentual_avis' in dados and 'tabe_prco' in dados:
            preco_base = float(dados['tabe_prco'])
            percentual = float(dados.pop('percentual_avis'))
            dados['tabe_avis'] = round(preco_base * (1 + percentual / 100), 2)

        if 'percentual_apra' in dados and 'tabe_prco' in dados:
            preco_base = float(dados['tabe_prco'])
            percentual = float(dados.pop('percentual_apra'))
            dados['tabe_apra'] = round(preco_base * (1 + percentual / 100), 2)

        # Remover campos que não são do modelo
        campos_validos = [f.name for f in Tabelaprecos._meta.fields]
        dados_limpos = {k: v for k, v in dados.items() if k in campos_validos}

        updated_instance = atualizar_preco_com_historico(banco, instance, dados_limpos)
        serializer = self.get_serializer(updated_instance)
        return Response(serializer.data)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
