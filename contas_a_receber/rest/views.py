import logging

from django.http import Http404
import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.timezone import now
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from core.decorator import ModuloRequeridoMixin
from core.registry import get_licenca_db_config
from Entidades.models import Entidades

from ..models import Titulosreceber, Baretitulos
from .serializers import (
    TitulosreceberSerializer,
    BaixaTitulosReceberSerializer,
    BaretitulosSerializer,
    ExcluirBaixaSerializer,
)
from .Views.createView import handle_create
from .Views.updateView import handle_update
from .Views.deleteView import handle_delete
from .Views.retrieveView import handle_retrieve
from ..services import baixar_titulo_receber, excluir_baixa_receber, reabrir_titulo_receber_sem_baixa

logger = logging.getLogger(__name__)

class TitulosreceberFilter(django_filters.FilterSet):
    titu_empr = django_filters.NumberFilter(field_name='titu_empr')
    titu_clie = django_filters.CharFilter(field_name='titu_clie', lookup_expr='exact')
    titu_situ = django_filters.CharFilter(field_name='titu_situ', lookup_expr='exact')
    titu_aber = django_filters.CharFilter(field_name='titu_aber', lookup_expr='exact')
    titu_venc__gte = django_filters.DateFilter(
        field_name='titu_venc',
        lookup_expr='gte',
        input_formats=[
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%S%z',
        ],
    )
    titu_venc__lte = django_filters.DateFilter(
        field_name='titu_venc',
        lookup_expr='lte',
        input_formats=[
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%S%z',
        ],
    )

    class Meta:
        model = Titulosreceber
        fields = []

class TitulosreceberViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    """CRUD de títulos a receber com ações de baixa, histórico e exclusão de baixas."""
    modulo_requerido = 'Financeiro'
    serializer_class = TitulosreceberSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TitulosreceberFilter
    search_fields = ['titu_titu', 'titu_clie', 'titu_aber']  
    ordering_fields = ['titu_venc', 'titu_valo']
    ordering = ['-titu_venc']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request)

        queryset = Titulosreceber.objects.using(banco).only(
            'titu_empr','titu_fili','titu_titu','titu_seri','titu_parc',
            'titu_clie','titu_valo','titu_emis','titu_venc','titu_situ',
            'titu_form_reci','titu_aber'
        )

        params = self.request.query_params
        possui_filtro_venc = any(
            k in params for k in ('titu_venc__gte', 'titu_venc__lte', 'titu_venc__gt', 'titu_venc__lt')
        )
        if not possui_filtro_venc:
            hoje = now().date()
            inicio_mes = hoje.replace(day=1)

            if inicio_mes.month == 12:
                fim_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1, day=1)
            else:
                fim_mes = inicio_mes.replace(month=inicio_mes.month + 1, day=1)

            queryset = queryset.filter(
                titu_venc__gte=inicio_mes,
                titu_venc__lt=fim_mes
            )

        cliente_nome = self.request.query_params.get('cliente_nome')
        empresa_id = self.request.query_params.get('titu_empr')

        if cliente_nome:
            ent_qs = Entidades.objects.using(banco).filter(
                enti_nome__icontains=cliente_nome
            )
            if empresa_id:
                ent_qs = ent_qs.filter(enti_empr=empresa_id)

            clientes_ids = list(ent_qs.values_list('enti_clie', flat=True))
            queryset = queryset.filter(
                titu_clie__in=clientes_ids
            ) if clientes_ids else queryset.none()

        return queryset 


    def _get_titulo_por_chave(self, *, incluir_aber=None):
        banco = get_licenca_db_config(self.request)
        try:
            qs = Titulosreceber.objects.using(banco).filter(
                titu_empr=self.kwargs['titu_empr'],
                titu_fili=self.kwargs['titu_fili'],
                titu_clie=self.kwargs['titu_clie'],
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

    def create(self, request, *args, **kwargs):
        """Cria um título a receber usando serviço de negócio."""
        try:
            return handle_create(self, request)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Atualiza um título a receber usando serviço de negócio."""
        try:
            return handle_update(self, request, partial=kwargs.pop('partial', False))
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Exclui um título a receber usando serviço de negócio."""
        return handle_delete(self, request)

    def retrieve(self, request, *args, **kwargs):
        return handle_retrieve(self, request)

    @action(detail=True, methods=['post'])
    def baixar_titulo(self, request, *args, **kwargs):
        try:
            titulo = self.get_object()
        except Http404:
            return Response(
                {'error': 'Título não encontrado ou já baixado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BaixaTitulosReceberSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        banco = get_licenca_db_config(request)
        usuario_id = getattr(request.user, 'usua_codi', None)

        try:
            baixa, lancamento = baixar_titulo_receber(
                titulo,
                banco=banco,
                dados=serializer.validated_data,
                usuario_id=usuario_id,
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
                'baixa_id': baixa.bare_sequ,
                'valor_recebido': str(baixa.bare_sub_tota),
                'status_titulo': baixa.bare_topa,
                'lancamento_id': lancamento.laba_ctrl if lancamento else None,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get'])
    def historico_baixas(self, request, *args, **kwargs):
        """Endpoint para consultar histórico de baixas de um título"""
        titulo = self.get_titulo_for_historico()  # Usar o novo método
        banco = get_licenca_db_config(request)
        
        baixas = Baretitulos.objects.using(banco).filter(
            bare_empr=titulo.titu_empr,
            bare_fili=titulo.titu_fili,
            bare_clie=titulo.titu_clie,
            bare_titu=titulo.titu_titu,  
            bare_seri=titulo.titu_seri,
            bare_parc=titulo.titu_parc
        ).order_by('-bare_dpag')
        
        serializer = BaretitulosSerializer(baixas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'])
    def excluir_baixa(self, request, *args, **kwargs):
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
            resultado = excluir_baixa_receber(titulo, int(baixa_id), banco=banco)
        except Baretitulos.DoesNotExist:
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

    @action(detail=True, methods=['post'])
    def reabrir_sem_baixa(self, request, *args, **kwargs):
        titulo = self.get_titulo_for_historico()
        banco = get_licenca_db_config(request)
        try:
            resultado = reabrir_titulo_receber_sem_baixa(titulo, banco=banco)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Erro inesperado ao reabrir (sem baixa) título %s", titulo.titu_titu)
            return Response({'error': 'Erro interno ao reabrir o título.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {
                'message': 'Título reaberto com sucesso.',
                **resultado,
            },
            status=status.HTTP_200_OK,
        )
