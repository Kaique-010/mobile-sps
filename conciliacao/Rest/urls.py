from django.urls import path

from .viewsets import ConciliacaoViewSet


app_name = "conciliacao_api"

urlpatterns = [
    path(
        "",
        ConciliacaoViewSet.as_view({"get": "list"}),
        name="lista",
    ),
    path(
        "ofx/importar/",
        ConciliacaoViewSet.as_view({"post": "importar_ofx"}),
        name="importar_ofx",
    ),
    path(
        "<int:empresa>/<int:filial>/<int:numero>/",
        ConciliacaoViewSet.as_view({"get": "retrieve"}),
        name="detalhe",
    ),
    path(
        "<int:empresa>/<int:filial>/<int:numero>/itens/",
        ConciliacaoViewSet.as_view({"get": "itens"}),
        name="itens",
    ),
]