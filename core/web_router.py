from django.urls import include, path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("home/", views.home, name="home"),
    path("<slug:slug>/home/", views.home, name="home_slug"),

    # Páginas web
    path("login/", views.web_login, name="web_login"),
    path("selecionar-empresa/", views.selecionar_empresa, name="selecionar_empresa"),

    path("onboarding/complete/<str:step>/", views.complete_onboarding_step, name="onboarding_complete"),
    path("<slug:slug>/series/", include("series.Web.web_urls")),
    path("<slug:slug>/entidades/", include("Entidades.web_urls")),
    path("<slug:slug>/produtos/", include("Produtos.Web.web_urls")),
    path("<slug:slug>/pedidos/", include("Pedidos.Web.web_urls")),
    path("<slug:slug>/orcamentos/", include("Orcamentos.Web.web_urls")),
    path("<slug:slug>/os/", include("O_S.Web.web_urls")),
    path("<slug:slug>/entradas/", include("Entradas_Estoque.Web.web_urls")),
    path("<slug:slug>/saidas/", include("Saidas_Estoque.Web.web_urls")),
    path(
        "<slug:slug>/centrosdecustos/",
        include(("CentrodeCustos.web_urls", "centrosdecustos"), namespace="centrosdecustos"),
    ),
    # Financeiro
    path("<slug:slug>/contas-a-pagar/", include("contas_a_pagar.Web.web_urls")),
    path("<slug:slug>/contas-a-receber/", include("contas_a_receber.Web.web_urls")),
    path("<slug:slug>/fluxo-de-caixa/", include("Financeiro.web_urls")),
    path("<slug:slug>/gerencial/", include("Gerencial.web_urls")),
    path("<slug:slug>/dre/", include("DRE.web_urls")),
    path("<slug:slug>/caixa-diario/", include("CaixaDiario.Web.web_urls")),
    path("<slug:slug>/licencas/", include("Licencas.web_urls")),
    path("<slug:slug>/onboarding/complete/<str:step>/", views.complete_onboarding_step, name="onboarding_complete_slug"),
    path("<slug:slug>/notas-destinadas/", include("NotasDestinadas.web_urls")),
    path("<slug:slug>/notas-fiscais/", include("Notas_Fiscais.Web.web_urls")),
    path("<slug:slug>/cfop/", include("CFOP.Web.urls")),
    path("<slug:slug>/boletos/", include("boletos.Web.urls")),
    path("<slug:slug>/importador/", include("importador.urls")),
    path("<slug:slug>/notificacoes/", include("notificacoes.Web.web_urls")),
    path("<slug:slug>/coleta-estoque/", include("coletaestoque.Web.web_urls")),
    path("<slug:slug>/controle-de-visitas/", include("controledevisitas.Web.web_urls")),
    path("<slug:slug>/central-de-ajuda/", include("centraldeajuda.urls")),
    path("<slug:slug>/parametros-admin/", include("parametros_admin.web_urls")),
]
