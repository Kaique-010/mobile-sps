from django.urls import path
from rest_framework.routers import DefaultRouter
from .viewsets import NotaViewSet, NotaEventoViewSet
from .autocomplete_viewsets import (
    EntidadeAutocompleteViewSet,
    ProdutoAutocompleteViewSet,
)
from Notas_Fiscais.api.views_financeiro import (
    ConsultarTitulosNotaView,
    GerarTitulosNotaView,
    RemoverTitulosNotaView,
    AtualizarTituloNotaView,
)
from .series_views import SeriesSaNotaView
from .autocomplete_extras_views import (
    ProdutoDetalheNotaView,
    CfopAutocompleteNotaView,
    TransportadorasAutocompleteNotaView,
)

router = DefaultRouter()
router.register(r"notas", NotaViewSet, basename="nota")
router.register(r"notas-eventos", NotaEventoViewSet, basename="nota-evento")
router.register(r"entidades-autocomplete", EntidadeAutocompleteViewSet, basename="entidade-autocomplete")
router.register(r"produtos-autocomplete", ProdutoAutocompleteViewSet, basename="produto-autocomplete")

urlpatterns = router.urls + [
    path("financeiro/<int:nota_id>/", ConsultarTitulosNotaView.as_view(), name="nota-financeiro-consultar"),
    path("financeiro/<int:nota_id>/gerar/", GerarTitulosNotaView.as_view(), name="nota-financeiro-gerar"),
    path("financeiro/<int:nota_id>/remover/", RemoverTitulosNotaView.as_view(), name="nota-financeiro-remover"),
    path("financeiro/<int:nota_id>/atualizar/", AtualizarTituloNotaView.as_view(), name="nota-financeiro-atualizar"),
    path("series/saida/", SeriesSaNotaView.as_view(), name="nota-series-saida"),
    path("produto-detalhe/<str:codigo>/", ProdutoDetalheNotaView.as_view(), name="nota-produto-detalhe"),
    path("cfop-autocomplete/", CfopAutocompleteNotaView.as_view(), name="nota-cfop-autocomplete"),
    path("transportadoras-autocomplete/", TransportadorasAutocompleteNotaView.as_view(), name="nota-transportadoras-autocomplete"),
]
