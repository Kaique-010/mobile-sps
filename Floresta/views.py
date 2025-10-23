from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from .models import Propriedades
from rest_framework.permissions import IsAuthenticated
from .serializers import PropriedadesSerializer 
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from core.utils import get_licenca_db_config

import logging

logger = logging.getLogger(__name__)


class PropriedadesViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    serializer_class = PropriedadesSerializer
    modulo_necessario = 'Pedidos'
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['prop_empr', 'prop_fili', 'prop_inat']
    search_fields = ['prop_nome', 'prop_codi', 'prop_sigl']

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")
        
        queryset = Propriedades.objects.using(banco).all().order_by('prop_nome')
        logger.info(f"Propriedades carregadas")
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def destroy(self, request, *args, **kwargs):
        """Override para adicionar validações antes da exclusão"""
        propriedade = self.get_object()
        banco = get_licenca_db_config(self.request)

        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        # Aqui você pode adicionar validações específicas antes da exclusão
        # Por exemplo, verificar se há registros dependentes
        
        logger.info(f"🗑️ Exclusão da propriedade {propriedade.prop_nome} iniciada")
        response = super().destroy(request, *args, **kwargs)
        logger.info(f"🗑️ Exclusão da propriedade concluída")
        
        return response



from rest_framework.decorators import api_view
from rest_framework.response import Response
from .services.dashboard_service import DashboardService

@api_view(["GET"])
def fluxo_gerencial(request, slug=None):
    """
    Retorna o dashboard de centro de custo anual com estrutura hierárquica.
    """
    arvore = DashboardService.montar_arvore()
    flat = list(DashboardService._flatten(arvore))

    orcado_total = sum(float(i["orcado"] or 0) for i in flat)
    realizado_total = sum(float(i["realizado"] or 0) for i in flat)
    diferenca_total = realizado_total - orcado_total
    perc_execucao_total = round((realizado_total / orcado_total * 100), 1) if orcado_total else 0

    return Response({
        "orcado_total": orcado_total,
        "realizado_total": realizado_total,
        "diferenca_total": diferenca_total,
        "perc_execucao_total": perc_execucao_total,
        "centros_custo": arvore
    })
