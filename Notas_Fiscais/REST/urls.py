# notas_fiscais/api/urls.py

from rest_framework.routers import DefaultRouter
from .viewsets import NotaViewSet, NotaEventoViewSet
from .autocomplete_viewsets import (
    EntidadeAutocompleteViewSet,
    ProdutoAutocompleteViewSet,
)

router = DefaultRouter()
router.register(r"notas", NotaViewSet, basename="nota")
router.register(r"notas-eventos", NotaEventoViewSet, basename="nota-evento")
router.register(r"entidades-autocomplete", EntidadeAutocompleteViewSet, basename="entidade-autocomplete")
router.register(r"produtos-autocomplete", ProdutoAutocompleteViewSet, basename="produto-autocomplete")

urlpatterns = router.urls
