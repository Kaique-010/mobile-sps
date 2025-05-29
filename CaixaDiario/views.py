from rest_framework import viewsets, status, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.db import transaction
from rest_framework.response import Response
from core.registry import get_licenca_db_config
from rest_framework.permissions import IsAuthenticated
import logging

from .models import Caixageral, Movicaixa
from .serializers import CaixageralSerializer, MovicaixaSerializer  

logger = logging.getLogger(__name__)

class CaixageralViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CaixageralSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['caix_empr', 'caix_fili', 'caix_caix', 'caix_data']
    search_fields = ['caix_ecf', 'caix_obse_fech']
    ordering_fields = ['caix_data', 'caix_hora']
    ordering = ['caix_data']
    lookup_field = 'caix_empr'  # ajuste se quiser chave composta, mas Django não gerencia isso direto

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.headers.get("X-Empresa")
        filial_id = self.request.headers.get("X-Filial")

        if banco and empresa_id and filial_id:
            queryset = Caixageral.objects.using(banco).filter(
                caix_empr=empresa_id,
                caix_fili=filial_id
            )
            return queryset
        return Caixageral.objects.none()

    def destroy(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request)
        instance = self.get_object()

        # Exemplo básico: não deixar excluir se tiver algo associado (ajuste conforme regra)
        # Aqui só deixei para excluir direto, adapte se precisar de regra.
        with transaction.atomic(using=banco):
            instance.delete()
            logger.info(f"🗑️ Exclusão de Caixageral ID {instance.caix_empr} concluída")

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context


class MovicaixaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MovicaixaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['movi_empr', 'movi_fili', 'movi_caix', 'movi_data']
    search_fields = ['movi_nomi', 'movi_obse']
    ordering_fields = ['movi_data', 'movi_hora']
    ordering = ['movi_data']
    lookup_field = 'movi_empr'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.headers.get("X-Empresa")
        filial_id = self.request.headers.get("X-Filial")

        if banco and empresa_id and filial_id:
            queryset = Movicaixa.objects.using(banco).filter(
                movi_empr=empresa_id,
                movi_fili=filial_id
            )
            return queryset
        return Movicaixa.objects.none()

    def destroy(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request)
        instance = self.get_object()

        # Igual no Caixageral, exemplo simples
        with transaction.atomic(using=banco):
            instance.delete()
            logger.info(f"🗑️ Exclusão de Movicaixa ID {instance.movi_empr} concluída")

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
