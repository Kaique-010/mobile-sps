from django.urls import path

from .views.create import importar
from .views.detail import detalhe
from .views.list import listar
from .views.conciliar import conciliar
from .views.titulos import buscar_titulos_abertos
from .views.detalhe_vinculos import detalhe_vinculos
from .views.desvincular import desvincular



app_name = "conciliacao"

urlpatterns = [
    path("", listar, name="listar"),
    path("importar/", importar, name="importar"),
    path(
        "<int:empresa>/<int:filial>/<int:numero>/",
        detalhe,
        name="detalhe",
    ),
    path(
        "<int:empresa>/<int:filial>/<int:numero>/conciliar/",
        conciliar,
        name="conciliar",
    ),
    path(
        "<int:empresa>/<int:filial>/<int:numero>/titulos-abertos/",
        buscar_titulos_abertos,
        name="titulos_abertos",
    ),
    path(
        "<int:empresa>/<int:filial>/<int:numero>/desvincular/",
        desvincular,
        name="desvincular",
    ),
    path(
        "<int:empresa>/<int:filial>/<int:numero>/detalhe-vinculos/<int:item_id>/",
        detalhe_vinculos,
        name="detalhe_vinculos",
    ),
]