from rest_framework.viewsets import ModelViewSet
from rest_framework import status, filters
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from django.db import transaction, IntegrityError
from django.db.models import Max
from .permissions import PodeVerOrdemDoSetor
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from core.decorator import modulo_necessario, ModuloRequeridoMixin

from .models import (
    Ordemservico,
    Ordemservicopecas,
    Ordemservicoservicos,
    Ordemservicoimgantes,
    Ordemservicoimgdurante,
    Ordemservicoimgdepois
)
from .serializers import (
    OrdemServicoSerializer,
    OrdemServicoPecasSerializer,
    OrdemServicoServicosSerializer,
    ImagemAntesSerializer,
    ImagemDuranteSerializer,
    ImagemDepoisSerializer,
)

import logging
logger = logging.getLogger(__name__)


class BaseMultiDBModelViewSet(ModuloRequeridoMixin, ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_banco(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error(f"Banco de dados não encontrado para {self.__class__.__name__}")
            raise NotFound("Banco de dados não encontrado.")
        return banco
    
    def get_queryset(self):
        banco = self.get_banco()
        qs = super().get_queryset()
        return qs.using(banco)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context

    @transaction.atomic(using='default')  # ou o default do seu banco principal, não do banco multi
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        data = request.data.copy()

        agora = timezone.localtime()
        data['orde_data_aber'] = agora.date()
        data['orde_hora_aber'] = agora.time().replace(microsecond=0)
        data['orde_stat_orde'] = 0

        # Sequencial (se quiser)
        data['orde_nume'] = self.get_next_ordem_numero(data.get('orde_empr'), data.get('orde_fili'))

        if request.user and request.user.pk:
            data['orde_usua_aber'] = request.user.pk

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic(using=banco):
            instance = serializer.save()

        logger.info(f"O.S. {instance.orde_nume} aberta por user {request.user.pk if request.user else 'anon'}")
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


    @transaction.atomic
    def update(self, request, *args, **kwargs):
        banco = self.get_banco()
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            with transaction.atomic(using=banco):
                serializer.save()
            logger.info(f"{self.__class__.__name__} ID {instance.pk} atualizado por user {request.user.pk if request.user else 'anon'}")
            return Response(serializer.data)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            logger.error(f"Erro de integridade na atualização {self.__class__.__name__}: {e}")
            return Response({"detail": "Erro de integridade."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Erro inesperado na atualização {self.__class__.__name__}: {e}")
            return Response({"detail": "Erro interno."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrdemServicoViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'ordemservico'
    serializer_class = OrdemServicoSerializer
    ffilter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['orde_stat_orde', 'orde_prio', 'orde_tipo', 'orde_enti']
    ordering_fields = ['orde_data_aber', 'orde_data_fech', 'orde_prio']
    search_fields = ['orde_prob', 'orde_defe_desc', 'orde_obse']
    permission_classes = [IsAuthenticated, PodeVerOrdemDoSetor]

    def get_queryset(self):
        banco = self.get_banco()
        user_setor = self.request.user.setor

        if user_setor.osfs_codi == 6:  
            return Ordemservico.objects.using(banco).all().order_by('orde_data_aber')
        else:
            return Ordemservico.objects.using(banco).filter(orde_seto=user_setor.osfs_codi).order_by('orde_data_aber')
    
    
    def get_next_ordem_numero(self, empre, fili):
        banco = self.get_banco()
        ultimo_numero = Ordemservico.objects.using(banco).filter(orde_empr=empre, orde_fili=fili).aggregate(Max('orde_nume'))['orde_nume__max']
        return (ultimo_numero or 0) + 1
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        data = request.data.copy()

        # Setar data e hora da abertura na criação
        agora = timezone.now()
        data['orde_data_aber'] = agora.date()
        data['orde_hora_aber'] = agora.time().replace(microsecond=0)

        # Status inicial Aberta (0)
        data['orde_stat_orde'] = 0

        # Se quiser guardar quem abriu a O.S. (campo orde_usua_aber)
        if request.user and request.user.pk:
            data['orde_usua_aber'] = request.user.pk

        # Aqui você tem que definir o número da ordem
        empre = data.get('orde_empr') or data.get('empr')
        fili = data.get('orde_fili') or data.get('fili')

        if not empre or not fili:
            return Response({"detail": "Empresa (orde_empr) e Filial (orde_fili) são obrigatórios."}, status=400)

        data['orde_nume'] = self.get_next_ordem_numero(empre, fili)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic(using=banco):
            instance = serializer.save()
        
        logger.info(f"O.S. {instance.orde_nume} aberta por user {request.user.pk if request.user else 'anon'}")
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)



class OrdemServicoPecasViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'ordemservico'
    serializer_class = OrdemServicoPecasSerializer

    def get_queryset(self):
        banco = self.get_banco()
        return Ordemservicopecas.objects.using(banco).all()

    def perform_create(self, serializer):
        banco = self.get_banco()
        with transaction.atomic(using=banco):
            serializer.save()
    
    def update(self, request, *args, **kwargs):
        banco = self.get_banco()
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic(using=banco):
            serializer.save()

        return Response(serializer.data)

class OrdemServicoServicosViewSet(BaseMultiDBModelViewSet):
    serializer_class = OrdemServicoServicosSerializer
    modulo_necessario = 'ordemservico'

    def get_queryset(self):
        return Ordemservicoservicos.objects.using(self.get_banco()).all()

    def perform_create(self, serializer):
        banco = self.get_banco()
        with transaction.atomic(using=banco):
            serializer.save()

    def update(self, request, *args, **kwargs):
        banco = self.get_banco()
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic(using=banco):
            serializer.save()

        return Response(serializer.data)




class ImagemAntesViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'ordemservico'
    serializer_class = ImagemAntesSerializer

    def get_queryset(self):
        banco = self.get_banco()
        return Ordemservicoimgantes.objects.using(banco).all()


class ImagemDuranteViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'ordemservico'
    serializer_class = ImagemDuranteSerializer

    def get_queryset(self):
        banco = self.get_banco()
        return Ordemservicoimgdurante.objects.using(banco).all()


class ImagemDepoisViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'ordemservico'
    serializer_class = ImagemDepoisSerializer

    def get_queryset(self):
        banco = self.get_banco()
        return Ordemservicoimgdepois.objects.using(banco).all()
