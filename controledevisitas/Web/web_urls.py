from django.urls import path
from .Views.list import ControleVisitaListView, ControleVisitaResumoView, ProximasVisitasDashboardView
from .Views.registrar import RegistrarItemVisitaView, ControleVisitaCreateView, ControleVisitaEditView


urlpatterns = [
    path('', ControleVisitaListView.as_view(), name='visitas_list_web'),
    path('resumo/<int:ctrl_id>/', ControleVisitaResumoView.as_view(), name='visita_resumo_web'),
    path('novo-item/<int:ctrl_id>/', RegistrarItemVisitaView.as_view(), name='visita_novo_item_web'),
    path('dashboard/', ProximasVisitasDashboardView.as_view(), name='visitas_dashboard_web'),
    path('nova/', ControleVisitaCreateView.as_view(), name='visita_criar_web'),
    path('editar/<int:ctrl_id>/', ControleVisitaEditView.as_view(), name='visita_editar_web'),
]
