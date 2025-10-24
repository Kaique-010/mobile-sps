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
from rest_framework.exceptions import NotFound
from core.utils import get_licenca_db_config
from .services.dashboard_service import DashboardService
from .serializers import DashboardCentroCustoAnualSerializer



@api_view(["GET"])
def fluxo_gerencial(request, slug=None):
    banco = get_licenca_db_config(request)
    if not banco:
        raise NotFound("Banco não encontrado")

    mes_ini = request.GET.get("mes_ini")
    mes_fim = request.GET.get("mes_fim")
    nivel = request.GET.get("nivel")
    tipo = request.GET.get("tipo")
    busca = request.GET.get("busca")

    arvore = DashboardService.montar_arvore(
        banco, 
        mes_ini=mes_ini, 
        mes_fim=mes_fim,
        nivel=nivel,
        tipo=tipo,
        busca=busca
    )
    flat = list(DashboardService._flatten(arvore))

    orcado_total = sum(float(i["orcado"] or 0) for i in flat)
    realizado_total = sum(float(i["realizado"] or 0) for i in flat)
    diferenca_total = realizado_total - orcado_total
    perc_execucao_total = round((realizado_total / orcado_total * 100), 1) if orcado_total else 0

    serializer = DashboardCentroCustoAnualSerializer(arvore, many=True)
    return Response({
        "orcado_total": orcado_total,
        "realizado_total": realizado_total,
        "diferenca_total": diferenca_total,
        "perc_execucao_total": perc_execucao_total,
        "centros_custo": serializer.data
    })
