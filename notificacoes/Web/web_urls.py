from django.urls import path
from .web_views import (
    NotificacoesDashboardView,
    TitulosCriadosHojeListView,
    TitulosAPagarListView,
    TitulosAReceberListView,
    OrcamentosHojeListView,
    PedidosHojeListView,
)

app_name = 'notificacoes_web'

urlpatterns = [
    path('', NotificacoesDashboardView.as_view(), name='dashboard'),
    path('titulos-criados-hoje/', TitulosCriadosHojeListView.as_view(), name='titulos_criados_hoje'),
    path('pagar/', TitulosAPagarListView.as_view(), name='pagar'),
    path('receber/', TitulosAReceberListView.as_view(), name='receber'),
    path('orcamentos/', OrcamentosHojeListView.as_view(), name='orcamentos_hoje'),
    path('pedidos/', PedidosHojeListView.as_view(), name='pedidos_hoje'),
]

