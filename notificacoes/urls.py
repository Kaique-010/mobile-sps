from django.urls import path
from .views import (
    NotificaEstoqueView,
    NotificaFinanceiroView, 
    NotificaVendasView,
    NotificaResumoView,
    NotificacaoListView
)

urlpatterns = [
    path('estoque/', NotificaEstoqueView.as_view(), name='notifica-estoque'),
    path('financeiro/', NotificaFinanceiroView.as_view(), name='notifica-financeiro'),
    path('vendas/', NotificaVendasView.as_view(), name='notifica-vendas'),
    path('resumo/', NotificaResumoView.as_view(), name='notifica-resumo'),
    path('listar/', NotificacaoListView.as_view(), name='listar-notificacoes'),
    path('marcar-lida/<int:notificacao_id>/', NotificacaoListView.as_view(), name='marcar-lida'),
]