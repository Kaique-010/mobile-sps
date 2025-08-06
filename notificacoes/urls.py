from django.urls import path
from .views import (
    NotificaEstoqueView,
    NotificaFinanceiroView, 
    NotificaVendasView,
    NotificaResumoView,
    NotificacaoListView,
    NotificaTudoView,
    LimparNotificacoesView,
    StatusNotificacoesView,
    GerarNotificacoesBadgeView
)

urlpatterns = [
    path('estoque/', NotificaEstoqueView.as_view(), name='notifica-estoque'),
    path('financeiro/', NotificaFinanceiroView.as_view(), name='notifica-financeiro'),
    path('vendas/', NotificaVendasView.as_view(), name='notifica-vendas'),
    path('resumo/', NotificaResumoView.as_view(), name='notifica-resumo'),
    path('tudo/', NotificaTudoView.as_view(), name='notifica-tudo'),
    path('listar/', NotificacaoListView.as_view(), name='listar-notificacoes'),
    path('marcar-lida/<int:notificacao_id>/', NotificacaoListView.as_view(), name='marcar-lida'),
    path('limpar/', LimparNotificacoesView.as_view(), name='limpar-notificacoes'),
    path('status/', StatusNotificacoesView.as_view(), name='status-notificacoes'),
    path('status/<slug:slug>/', StatusNotificacoesView.as_view(), name='status-notificacoes-slug'),
    
    # Endpoint para gerar notificações SOB DEMANDA (quando clicar no badge)
    path('gerar-badge/', GerarNotificacoesBadgeView.as_view(), name='gerar-notificacoes-badge'),
    path('gerar-badge/<slug:slug>/', GerarNotificacoesBadgeView.as_view(), name='gerar-notificacoes-badge-slug'),
]