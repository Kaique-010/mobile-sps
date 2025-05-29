from rest_framework.viewsets import ModelViewSet
from rest_framework import status, filters
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from django.db import transaction, IntegrityError
from .permissions import PodeVerOrdemDoSetor
from core.middleware import get_licenca_db_config
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

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            with transaction.atomic(using=banco):
                serializer.save()
            logger.info(f"{self.__class__.__name__} criado por user {request.user.pk if request.user else 'anon'}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            logger.error(f"Erro de integridade na criação {self.__class__.__name__}: {e}")
            return Response({"detail": "Erro de integridade."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Erro inesperado na criação {self.__class__.__name__}: {e}")
            return Response({"detail": "Erro interno."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    filter_backends = [filters.OrderingFilter, filters.SearchFilter, filters.DjangoFilterBackend]
    filterset_fields = ['orde_stat', 'orde_prio', 'orde_tipo', 'orde_enti']
    ordering_fields = ['orde_data_aber', 'orde_data_fech', 'orde_prio']
    search_fields = ['orde_prob', 'orde_defe_desc', 'orde_obse']
    permission_classes = [IsAuthenticated, PodeVerOrdemDoSetor]

    def get_queryset(self):
        banco = self.get_banco()
        user_setor = self.request.user.setor
        return Ordemservico.objects.using(banco).filter(orde_setor=user_setor).order_by('orde_data_aber')


class OrdemServicoPecasViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'ordemservico'
    serializer_class = OrdemServicoPecasSerializer

    def get_queryset(self):
        banco = self.get_banco()
        return Ordemservicopecas.objects.using(banco).all()


class OrdemServicoServicosViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'ordemservico'
    serializer_class = OrdemServicoServicosSerializer

    def get_queryset(self):
        banco = self.get_banco()
        return Ordemservicoservicos.objects.using(banco).all()


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
