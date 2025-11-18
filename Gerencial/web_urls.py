from django.urls import path
from .web_views import ExtratoMovimentacaoProdutosWebView

app_name = "GerencialWeb"

urlpatterns = [
    path("estoque/movimentacao/", ExtratoMovimentacaoProdutosWebView.as_view(), name="extrato_movimentacao_produtos"),
]