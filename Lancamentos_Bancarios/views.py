from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from .models import Lctobancario
from rest_framework.permissions import IsAuthenticated
from .serializers import LctobancarioSerializer
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from core.utils import get_licenca_db_config

import logging

logger = logging.getLogger(__name__)


class LctobancarioViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    serializer_class = LctobancarioSerializer
    modulo_necessario = 'Financeiro'
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['laba_empr', 'laba_fili', 'laba_ctrl']
    search_fields = ['laba_data', 'laba_ctrl']
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")
        
        queryset = Lctobancario.objects.using(banco).all().order_by('laba_data')
        logger.info(f"Lctobancario carregados")
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
    
    def destroy(self, request, *args, **kwargs):
        """Override para adicionar validações antes da exclusão"""
        lctobancario = self.get_object()
        banco = get_licenca_db_config(self.request)

        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        # Aqui você pode adicionar validações específicas antes da exclusão
        # Por exemplo, verificar se há registros dependentes
        
        logger.info(f"🗑️ Exclusão do lctobancario {lctobancario.laba_ctrl} iniciada")
        response = super().destroy(request, *args, **kwargs)
        logger.info(f"🗑️ Exclusão do lctobancario concluída")
        
        return response