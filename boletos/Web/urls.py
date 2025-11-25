from django.urls import path
from .views.titulo_cbv import GerarBoletoWebView
from .views.cnab_cbv import GerarRemessaWebView, ProcessarRetornoWebView
from .views.banco_cbv import ListaBancosView, BancoConfigListView, BancoConfigUpdateView, BancoConfigCreateView
from .views.carteira_cbv import (
    CarteiraListView,
    CarteiraCreateView,
    CarteiraUpdateView,
    CarteiraLookupView,
    CarteiraNextCodeView,
)
from .views.logo_cbv import LogoView

urlpatterns = [
    path("titulo/<int:pk>/gerar/", GerarBoletoWebView.as_view(), name="boleto_web_gerar"),
    path("bordero/<int:pk>/remessa/", GerarRemessaWebView.as_view(), name="remessa_web_gerar"),
    path("retorno/", ProcessarRetornoWebView.as_view(), name="retorno_web_processar"),
    path("bancos/", ListaBancosView.as_view(), name="lista_bancos"),
    path("bancos/configuracao/", BancoConfigListView.as_view(), name="banco_config_list"),
    path("bancos/configuracao/criar/", BancoConfigCreateView.as_view(), name="banco_config_criar"),
    path("bancos/configuracao/<int:enti_clie>/editar/", BancoConfigUpdateView.as_view(), name="banco_config_editar"),
    path("logos/<str:variation>/<str:codigo>.bmp", LogoView.as_view(), name="boleto_logo"),
    path("carteiras/", CarteiraListView.as_view(), name="carteira_list"),
    path("carteiras/criar/", CarteiraCreateView.as_view(), name="carteira_criar"),
    path("carteiras/<int:codigo>/editar/", CarteiraUpdateView.as_view(), name="carteira_editar"),
    path("carteiras/lookup/", CarteiraLookupView.as_view(), name="carteira_lookup"),
    path("carteiras/proximo/", CarteiraNextCodeView.as_view(), name="carteira_proximo"),
]
