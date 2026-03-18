from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, F, Q
from django.core.exceptions import FieldError
from django.db.models import Value
from django.db.models.functions import Coalesce

from core.decorator import ModuloRequeridoMixin
from core.registry import get_licenca_db_config
from core.middleware import get_licenca_slug

from ..models import ProdutosDetalhados
from ..serializers.produto_serializer import ProdutoDetalhadoSerializer
from logging import getLogger

logger = getLogger(__name__)

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
        banco = get_licenca_db_config(self.request)
        qs = ProdutosDetalhados.objects.using(banco).all().annotate(
            _saldo=Coalesce('saldo', Value(0))
        )

        empresa = (
            self.request.query_params.get('empresa')
            or self.request.headers.get('X-Empresa')
            or self.request.headers.get('X-EmpresaID')
            or self.request.headers.get('Empresa_id')
            or getattr(self.request, 'empresa', None)
            or self.request.session.get('empresa_id')
        )

        filial = (
            self.request.query_params.get('filial')
            or self.request.headers.get('X-Filial')
            or self.request.headers.get('X-FilialID')
            or self.request.headers.get('Filial_id')
            or getattr(self.request, 'filial', None)
            or self.request.session.get('filial_id')
        )

        marca_nome = self.request.query_params.get('marca_nome')
        if marca_nome:
            if marca_nome == '__sem_marca__':
                qs = qs.filter(Q(marca_nome__isnull=True) | Q(marca_nome=''))
            else:
                qs = qs.filter(marca_nome=marca_nome)

        if empresa:
            try:
                empresa_int = int(str(empresa))
                qs = qs.filter(
                    Q(empresa=empresa_int)
                    | Q(empresa=0)
                    | Q(empresa__isnull=True)
                )
            except (TypeError, ValueError):
                qs = qs.filter(
                    Q(empresa=empresa)
                    | Q(empresa=0)
                    | Q(empresa__isnull=True)
                )
        if filial:
            try:
                filial_int = int(str(filial))
                qs = qs.filter(
                    Q(filial=filial_int)
                    | Q(filial=0)
                    | Q(filial__isnull=True)
                )
            except (TypeError, ValueError):
                qs = qs.filter(
                    Q(filial=filial)
                    | Q(filial=0)
                    | Q(filial__isnull=True)
                )

        def _is_true(value):
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in ('true', '1', 't', 'yes', 'y')

        com_saldo = self.request.query_params.get('com_saldo')
        sem_saldo = self.request.query_params.get('sem_saldo')
        estoque_minimo = self.request.query_params.get('estoque_minimo')

        if _is_true(com_saldo):
            qs = qs.filter(saldo__gt=0)
        elif _is_true(sem_saldo):
            qs = qs.filter(Q(saldo__isnull=True) | Q(saldo__lte=0))
        elif _is_true(estoque_minimo):
            try:
                qs = qs.filter(_saldo__lt=F('estoque_minimo'))
            except FieldError:
                pass

        logger.info(
            "Listar produtos detalhados com filtro: empresa=%s, filial=%s, marca=%s, com_saldo=%s, sem_saldo=%s, estoque_minimo=%s",
            empresa,
            filial,
            marca_nome,
            com_saldo,
            sem_saldo,
            estoque_minimo,
        )
        return qs


class EstoqueResumoView(APIView):
    permission_classes = [IsAuthenticated]
    modulo_necessario = 'dash'

    def get(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        qs = ProdutosDetalhados.objects.using(banco).all()

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
