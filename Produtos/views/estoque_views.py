from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, F, Q

from core.decorator import ModuloRequeridoMixin
from core.registry import get_licenca_db_config
from core.middleware import get_licenca_slug

from ..models import ProdutosDetalhados
from ..serializers.produto_serializer import ProdutoDetalhadoSerializer

class ProdutosDetalhadosViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_necessario = 'Produtos'
    serializer_class = ProdutoDetalhadoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['codigo', 'nome', 'marca_nome', 'empresa', 'filial']
    search_fields = ['codigo', 'nome', 'marca_nome']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def get_queryset(self, slug=None):
        slug = get_licenca_slug()
        qs = ProdutosDetalhados.objects.using(slug).all()

        empresa = self.request.query_params.get('empresa') or \
                  self.request.headers.get('X-Empresa') or \
                  self.request.session.get('empresa_id')

        filial = self.request.query_params.get('filial') or \
                 self.request.headers.get('X-Filial') or \
                 self.request.session.get('filial_id')

        if marca_nome := self.request.query_params.get('marca_nome'):
            if marca_nome == '__sem_marca__':
                qs = qs.filter(Q(marca_nome__isnull=True) | Q(marca_nome=''))
            else:
                qs = qs.filter(marca_nome=marca_nome)

        if empresa:
            qs = qs.filter(empresa=empresa)
        if filial:
            qs = qs.filter(filial=filial)

        # Filtros de estoque
        com_saldo = self.request.query_params.get('com_saldo')
        sem_saldo = self.request.query_params.get('sem_saldo')
        estoque_minimo = self.request.query_params.get('estoque_minimo')  
        
        if com_saldo == 'true':
            qs = qs.filter(saldo__gt=0)
        elif sem_saldo == 'true':
            qs = qs.filter(saldo=0)
        elif estoque_minimo == 'true':
            qs = qs.filter(saldo__lt=F('estoque_minimo'))

        return qs


class EstoqueResumoView(APIView):
    permission_classes = [IsAuthenticated]
    modulo_necessario = 'dash'

    def get(self, request, *args, **kwargs):
        slug = get_licenca_slug()
        qs = ProdutosDetalhados.objects.using(slug).all()

        # Filtros opcionais
        marca = request.query_params.get('marca')
        grupo = request.query_params.get('grupo')
        empresa = request.query_params.get('empresa')
        filial = request.query_params.get('filial')

        if marca == '__sem_marca__':
            qs = qs.filter(marca_nome__isnull=True)
        elif marca:
            qs = qs.filter(marca_nome=marca)

        if grupo:
            qs = qs.filter(grupo_id=grupo)

        if empresa:
            qs = qs.filter(empresa=empresa)

        if filial:
            qs = qs.filter(filial=filial)

        resumo = qs.aggregate(
            total_estoque=Sum('valor_total_estoque'),
            quantidade_itens=Sum('saldo')
        )

        return Response(resumo)
