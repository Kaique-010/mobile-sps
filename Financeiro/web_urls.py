from django.urls import path
from .web_views import FluxoCaixaView, FluxoCompetenciaView, DetalhesCaixaView, DetalhesCompetenciaView

app_name = "financeiro_web"

urlpatterns = [
    path("", FluxoCaixaView.as_view(), name="fluxo_de_caixa"),
    path("fluxo-competencia/", FluxoCompetenciaView.as_view(), name="fluxo_competencia"),
    path("detalhes/caixa/<int:year>/<int:month>/", DetalhesCaixaView.as_view(), name="detalhes_caixa"),
    path("detalhes/competencia/<int:year>/<int:month>/", DetalhesCompetenciaView.as_view(), name="detalhes_competencia"),
]
