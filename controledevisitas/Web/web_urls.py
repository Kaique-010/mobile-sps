from django.urls import path
from Pisos.views import DashPedidosPisosView
from .Views.list import ControleVisitaListView, ControleVisitaResumoView, ProximasVisitasDashboardView
from .Views.registrar import RegistrarItemVisitaView, ControleVisitaCreateView, ControleVisitaEditView
from .Views.etapas import (
    EtapaVisitaListView,
    EtapaVisitaCreateView,
    EtapaVisitaUpdateView,
    EtapaVisitaDeleteView,
)


urlpatterns = [
    path('', ControleVisitaListView.as_view(), name='visitas_list_web'),
    path('resumo/<int:ctrl_id>/', ControleVisitaResumoView.as_view(), name='visita_resumo_web'),
    path('novo-item/<int:ctrl_id>/', RegistrarItemVisitaView.as_view(), name='visita_novo_item_web'),
    path('dashboard/', ProximasVisitasDashboardView.as_view(), name='visitas_dashboard_web'),
    path('dashboard-pisos/', DashPedidosPisosView.as_view(), name='dashboard_pedidos_pisos_web'),
    path('nova/', ControleVisitaCreateView.as_view(), name='visita_criar_web'),
    path('editar/<int:ctrl_id>/', ControleVisitaEditView.as_view(), name='visita_editar_web'),
    # Etapas
    path('etapas/', EtapaVisitaListView.as_view(), name='etapas_list_web'),
    path('etapas/nova/', EtapaVisitaCreateView.as_view(), name='etapa_criar_web'),
    path('etapas/editar/<int:etap_id>/', EtapaVisitaUpdateView.as_view(), name='etapa_editar_web'),
    path('etapas/excluir/<int:etap_id>/', EtapaVisitaDeleteView.as_view(), name='etapa_excluir_web'),
]
