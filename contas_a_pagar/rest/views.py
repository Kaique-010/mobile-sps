import logging

from django.db import transaction
from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.timezone import now
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from core.decorator import ModuloRequeridoMixin
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from Entidades.models import Entidades

from ..models import Titulospagar, Bapatitulos
from .serializers import (
    TitulospagarSerializer,
    BaixaTitulosPagarSerializer,
    BapatitulosSerializer,
    ExcluirBaixaSerializer,
)
from .Views.createView import handle_create
from .Views.updateView import handle_update
from .Views.deleteView import handle_delete
from .Views.retrieveView import handle_retrieve
from ..services import baixar_titulo_pagar, excluir_baixa_titulo

logger = logging.getLogger(__name__)


class TitulospagarViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    """CRUD de títulos a pagar com ações de baixa e histórico."""

    modulo_requerido = 'Financeiro'
    serializer_class = TitulospagarSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'titu_empr': ['exact'],
        'titu_forn': ['exact'],
        'titu_titu': ['exact'],
        'titu_venc': ['gte', 'lte'],
        'titu_aber': ['exact'],
    }
    search_fields  = ['titu_titu', 'titu_aber']
    ordering_fields = ['titu_emis', 'titu_venc', 'titu_valo']
    ordering = ['-titu_emis']

    # ------------------------------------------------------------------
    # Contexto e queryset
    # ------------------------------------------------------------------

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        queryset = Titulospagar.objects.using(banco).all()

        hoje        = now().date()
        inicio_mes  = hoje.replace(day=1)
        if inicio_mes.month == 12:
            fim_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1, day=1)
        else:
            fim_mes = inicio_mes.replace(month=inicio_mes.month + 1, day=1)

        queryset = queryset.filter(titu_venc__gte=inicio_mes, titu_venc__lt=fim_mes)

        fornecedor_nome = self.request.query_params.get('fornecedor_nome')
        empresa_id      = self.request.query_params.get('titu_empr')

        if fornecedor_nome:
            ent_qs = Entidades.objects.using(banco).filter(enti_nome__icontains=fornecedor_nome)
            if empresa_id:
                ent_qs = ent_qs.filter(enti_empr=empresa_id)
            fornecedor_ids = list(ent_qs.values_list('enti_clie', flat=True))
            queryset = (
                queryset.filter(titu_forn__in=fornecedor_ids)
                if fornecedor_ids
                else queryset.none()
            )

        return queryset

    # ------------------------------------------------------------------
    # Lookup por chave composta
    # ------------------------------------------------------------------

    def _get_titulo_por_chave(self, *, incluir_aber=None):
        """
        Busca um Titulospagar pela chave composta dos kwargs da URL.
        incluir_aber: lista de valores de titu_aber a aceitar (None = todos).
        """
        banco = get_licenca_db_config(self.request)
        try:
            qs = Titulospagar.objects.using(banco).filter(
                titu_empr=self.kwargs['titu_empr'],
                titu_fili=self.kwargs['titu_fili'],
                titu_forn=self.kwargs['titu_forn'],
                titu_titu=self.kwargs['titu_titu'],
                titu_seri=self.kwargs['titu_seri'],
                titu_parc=self.kwargs['titu_parc'],
                titu_emis=self.kwargs['titu_emis'],
                titu_venc=self.kwargs['titu_venc'],
            )
            if incluir_aber:
                qs = qs.filter(titu_aber__in=incluir_aber)

            obj = qs.first()
            if obj is None:
                raise Http404("Título não encontrado.")
            if qs.count() > 1:
                logger.warning("Múltiplos títulos encontrados para %s — usando o primeiro.", self.kwargs)
            return obj
        except KeyError as exc:
            logger.error("Parâmetro obrigatório ausente: %s", exc)
            raise Http404(f"Parâmetro obrigatório ausente: {exc}")

    def get_object(self):
        return self._get_titulo_por_chave(incluir_aber=['A', 'P'])

    def get_titulo_for_historico(self):
        return self._get_titulo_por_chave()

    # ------------------------------------------------------------------
    # CRUD padrão (delegado para handlers existentes)
    # ------------------------------------------------------------------

    def create(self, request, *args, **kwargs):
        try:
            return handle_create(self, request)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            return handle_update(self, request, partial=kwargs.pop('partial', False))
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        return handle_delete(self, request)

    def retrieve(self, request, *args, **kwargs):
        return handle_retrieve(self, request)

    # ------------------------------------------------------------------
    # Histórico de baixas
    # ------------------------------------------------------------------

    @action(detail=True, methods=['get'])
    def historico_baixas(self, request, *args, **kwargs):
        titulo = self.get_titulo_for_historico()
        banco  = get_licenca_db_config(request)

        baixas = Bapatitulos.objects.using(banco).filter(
            bapa_empr=titulo.titu_empr,
            bapa_fili=titulo.titu_fili,
            bapa_forn=titulo.titu_forn,
            bapa_titu=titulo.titu_titu,
            bapa_seri=titulo.titu_seri,
            bapa_parc=titulo.titu_parc,
        ).order_by('-bapa_dpag')

        serializer = BapatitulosSerializer(baixas, many=True)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # Baixar título
    # ------------------------------------------------------------------

    @action(detail=True, methods=['post'])
    def baixar_titulo(self, request, *args, **kwargs):
        """Baixa (liquida) um título a pagar. Toda a lógica fica no service."""
        try:
            titulo = self.get_object()
        except Http404:
            return Response(
                {'error': 'Título não encontrado ou já baixado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BaixaTitulosPagarSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        banco = get_licenca_db_config(request)

        try:
            baixa, lancamento = baixar_titulo_pagar(
                titulo,
                banco=banco,
                dados=serializer.validated_data,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Erro inesperado ao baixar título %s", titulo.titu_titu)
            return Response(
                {'error': 'Erro interno ao processar a baixa.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                'message': 'Título baixado com sucesso.',
                'baixa_id': baixa.bapa_sequ,
                'valor_pago': str(baixa.bapa_sub_tota),
                'status_titulo': baixa.bapa_topa,
                'lancamento_id': lancamento.laba_ctrl if lancamento else None,
            },
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------
    # Excluir baixa
    # ------------------------------------------------------------------

    @action(detail=True, methods=['delete'])
    def excluir_baixa(self, request, *args, **kwargs):
        """Exclui uma baixa específica e recalcula o status do título."""
        titulo = self.get_titulo_for_historico()

        baixa_id = request.query_params.get('baixa_id') or kwargs.get('baixa_id')
        if not baixa_id:
            return Response(
                {'error': 'O parâmetro baixa_id é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ExcluirBaixaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        banco = get_licenca_db_config(request)

        try:
            resultado = excluir_baixa_titulo(titulo, int(baixa_id), banco=banco)
        except Bapatitulos.DoesNotExist:
            return Response({'error': 'Baixa não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Erro inesperado ao excluir baixa %s", baixa_id)
            return Response(
                {'error': 'Erro interno ao excluir a baixa.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                'message': 'Baixa excluída com sucesso.',
                **resultado,
                'motivo': serializer.validated_data.get('motivo_exclusao', ''),
            },
            status=status.HTTP_200_OK,
        )