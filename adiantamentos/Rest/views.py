from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from core.decorator import ModuloRequeridoMixin
from core.utils import get_licenca_db_config
from ..models import Adiantamentos
from .serializers import AdiantamentosSerializer
from ..services import AdiantamentosService


class AdiantamentosViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_requerido = 'Financeiro'
    serializer_class = AdiantamentosSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'adia_empr': ['exact'],
        'adia_fili': ['exact'],
        'adia_enti': ['exact'],
        'adia_tipo': ['exact'],
    }
    search_fields = ['adia_docu', 'adia_seri']
    ordering_fields = ['adia_docu', 'adia_seri', 'adia_valo']
    ordering = ['adia_docu']

    def get_banco(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return banco

    def get_queryset(self):
        banco = self.get_banco()
        return Adiantamentos.objects.using(banco).all()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['banco'] = self.get_banco()
        return ctx

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['get'])
    def disponiveis(self, request, *args, **kwargs):
        """
        Lista adiantamentos com saldo > 0 para uma entidade/tipo.
        Parâmetros:
          - empresa (obrigatório)
          - filial (obrigatório)
          - entidade (obrigatório)
          - tipo (opcional: 'P' ou 'R')
        """
        banco = self.get_banco()
        empresa = request.query_params.get('empresa')
        filial = request.query_params.get('filial')
        entidade = request.query_params.get('entidade')
        tipo = request.query_params.get('tipo')

        if not empresa or not filial or not entidade:
            return Response(
                {'error': 'empresa, filial e entidade são obrigatórios'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = Adiantamentos.objects.using(banco).filter(
            adia_empr=empresa,
            adia_fili=filial,
            adia_enti=entidade,
            adia_sald__gt=0,
        )
        if tipo:
            qs = qs.filter(adia_tipo=tipo)

        qs = qs.order_by('adia_docu', 'adia_seri')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
