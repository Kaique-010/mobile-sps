from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import replace_query_param
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, F, Q
from django.core.exceptions import FieldError
from django.db.models import Value
from django.db.models.functions import Coalesce
import time
from django.db import connections
from core.decorator import ModuloRequeridoMixin
from core.registry import get_licenca_db_config
from core.middleware import get_licenca_slug

from ..models import ProdutosDetalhados
from ..serializers.produto_serializer import ProdutoDetalhadoSerializer
from logging import getLogger
from rest_framework.pagination import LimitOffsetPagination

class ProdutosDetalhadosPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 500

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        self.limit = self.get_limit(request)

        if self.limit is None:
            return None

        self.offset = self.get_offset(request)

        # Busca um registro extra para descobrir se existe próxima página.
        resultados = list(
            queryset[self.offset:self.offset + self.limit + 1]
        )

        self.has_next = len(resultados) > self.limit
        self.has_previous = self.offset > 0

        return resultados[:self.limit]

    def get_paginated_response(self, data):
        next_url = None
        previous_url = None

        if self.has_next:
            next_url = replace_query_param(
                self.request.build_absolute_uri(),
                self.offset_query_param,
                self.offset + self.limit
            )

        if self.has_previous:
            previous_url = replace_query_param(
                self.request.build_absolute_uri(),
                self.offset_query_param,
                max(self.offset - self.limit, 0)
            )

        return Response({
            'next': next_url,
            'previous': previous_url,
            'results': data
        })


logger = getLogger(__name__)

class ProdutosDetalhadosViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_necessario = 'Produtos'
    serializer_class = ProdutoDetalhadoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['codigo', 'nome', 'marca_nome', 'empresa', 'filial']
    search_fields = ['codigo', 'nome', 'marca_nome']
    pagination_class = ProdutosDetalhadosPagination

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    
    def get_queryset(self):
        inicio = time.perf_counter()

        logger.warning(
            "[PRODUTOS] INICIO get_queryset | path=%s | usuario=%s",
            self.request.path,
            self.request.user
        )

        banco = get_licenca_db_config(self.request)

        logger.warning(
            "[PRODUTOS] BANCO SELECIONADO: %s",
            banco
        )

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

        # Filtro por marca
        if marca_nome:
            if marca_nome == '__sem_marca__':
                qs = qs.filter(
                    Q(marca_nome__isnull=True) | Q(marca_nome='')
                )
            else:
                qs = qs.filter(marca_nome=marca_nome)

        # Filtro por empresa
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

        # Filtro por filial
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

        # Filtros de estoque
        def _is_true(value):
            if isinstance(value, bool):
                return value

            return str(value).strip().lower() in (
                'true', '1', 't', 'yes', 'y'
            )

        com_saldo = self.request.query_params.get('com_saldo')
        sem_saldo = self.request.query_params.get('sem_saldo')
        estoque_minimo = self.request.query_params.get('estoque_minimo')

        if _is_true(com_saldo):
            qs = qs.filter(saldo__gt=0)

        elif _is_true(sem_saldo):
            qs = qs.filter(
                Q(saldo__isnull=True) | Q(saldo__lte=0)
            )

        elif _is_true(estoque_minimo):
            try:
                qs = qs.filter(_saldo__lt=F('estoque_minimo'))
            except FieldError:
                logger.exception(
                    "[PRODUTOS] Erro ao aplicar filtro de estoque mínimo"
                )

        # Log dos filtros aplicados
        logger.info(
            "[PRODUTOS] FILTROS | empresa=%s | filial=%s | marca=%s | "
            "com_saldo=%s | sem_saldo=%s | estoque_minimo=%s",
            empresa,
            filial,
            marca_nome,
            com_saldo,
            sem_saldo,
            estoque_minimo
        )

        tempo_total = (time.perf_counter() - inicio) * 1000

        logger.warning(
            "[PRODUTOS] FIM get_queryset | banco=%s | tempo=%.2fms",
            banco,
            tempo_total
        )

        return qs

    
    def list(self, request, *args, **kwargs):
        inicio = time.perf_counter()
        consultas = []
        banco = get_licenca_db_config(request)

        def medir_sql(execute, sql, params, many, context):
            inicio_sql = time.perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                duracao = (time.perf_counter() - inicio_sql) * 1000
                consultas.append(duracao)

        with connections[banco].execute_wrapper(medir_sql):

            inicio_filtro = time.perf_counter()
            queryset = self.filter_queryset(self.get_queryset())
            tempo_filtro = (time.perf_counter() - inicio_filtro) * 1000

            inicio_paginacao = time.perf_counter()
            page = self.paginate_queryset(queryset)
            tempo_paginacao = (
                time.perf_counter() - inicio_paginacao
            ) * 1000

            inicio_serializer = time.perf_counter()
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
            tempo_serializer = (
                time.perf_counter() - inicio_serializer
            ) * 1000

            tempo_total = (time.perf_counter() - inicio) * 1000

            logger.info(
                "[PERFORMANCE PRODUTOS] "
                "banco=%s | "
                "registros=%s | "
                "filtro=%.2fms | "
                "paginacao=%.2fms | "
                "serializer=%.2fms | "
                "sql_total=%.2fms | "
                "sql_count=%s | "
                "total=%.2fms",
                banco,
                len(data),
                tempo_filtro,
                tempo_paginacao,
                tempo_serializer,
                sum(consultas),
                len(consultas),
                tempo_total,
            )

            return self.get_paginated_response(data)


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


class ZerarEstoqueView(APIView):
    permission_classes = [IsAuthenticated]
    modulo_necessario = 'Produtos'

    def _get_contexto(self, request):
        banco = get_licenca_db_config(request)
        empresa = (
            request.data.get('empresa')
            if isinstance(getattr(request, 'data', None), (dict,)) else None
        ) or request.query_params.get('empresa') or request.headers.get('X-Empresa') or request.session.get('empresa_id') or 1
        filial = (
            request.data.get('filial')
            if isinstance(getattr(request, 'data', None), (dict,)) else None
        ) or request.query_params.get('filial') or request.headers.get('X-Filial') or request.session.get('filial_id') or 1
        return banco, empresa, filial

    def get(self, request, *args, **kwargs):
        banco, empresa, filial = self._get_contexto(request)
        from Produtos.servicos.zerar_estoque import obter_saldos_atuais

        info = obter_saldos_atuais(
            banco=banco,
            empresa=empresa,
            filial=filial,
            apenas_com_saldo=True,
            limit=50,
        )
        return Response(
            {
                'banco': banco,
                'empresa': str(empresa),
                'filial': str(filial),
                'total_com_saldo': info.get('total', 0),
                'amostra': info.get('amostra', []),
            }
        )

    def post(self, request, *args, **kwargs):
        banco, empresa, filial = self._get_contexto(request)
        from Produtos.servicos.zerar_estoque import zerar_estoque

        batch_size = request.data.get('batch_size') if isinstance(getattr(request, 'data', None), (dict,)) else None
        limit_resultados = request.data.get('limit_resultados') if isinstance(getattr(request, 'data', None), (dict,)) else None
        resultado = zerar_estoque(
            banco=banco,
            empresa=empresa,
            filial=filial,
            batch_size=int(batch_size or 500),
            limit_resultados=None if limit_resultados is None else int(limit_resultados),
        )
        return Response({'banco': banco, **resultado})
