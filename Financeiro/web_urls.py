from django.urls import path
from Financeiro.Web.web_views import FluxoCaixaView, FluxoCompetenciaView, DetalhesCaixaView, DetalhesCompetenciaView
from Financeiro.Web.views import OrcamentoDashboardTemplateView, orcamento_realizado_detalhe
from Financeiro.Web.orcamento_views import OrcamentoCreateView, OrcamentoItemCreateView, orcamento_item_buscar
from Financeiro.Rest.autocomplete import autocomplete_cc







app_name = "financeiro_web"

urlpatterns = [
    path("", FluxoCaixaView.as_view(), name="fluxo_de_caixa"),
    path("fluxo-competencia/", FluxoCompetenciaView.as_view(), name="fluxo_competencia"),
    path("detalhes/caixa/<int:year>/<int:month>/", DetalhesCaixaView.as_view(), name="detalhes_caixa"),
    path("detalhes/competencia/<int:year>/<int:month>/", DetalhesCompetenciaView.as_view(), name="detalhes_competencia"),
    path("orcamento/dashboard/", OrcamentoDashboardTemplateView.as_view(), name="orcamento_dashboard"),
    path("orcamento/create/", OrcamentoCreateView.as_view(), name="orcamento_create"),
    path("orcamento/<int:orcamento_id>/item/buscar/", orcamento_item_buscar, name="orcamento_item_buscar"),
    path("orcamento/<int:orcamento_id>/item/create/", OrcamentoItemCreateView.as_view(), name="orcamento_item_create"),
    path("orcamento/realizado-detalhe/", orcamento_realizado_detalhe, name="orcamento_realizado_detalhe"),
    path("autocomplete/centrodecustos/", autocomplete_cc, name="autocomplete_centrosdecustos"),
]
