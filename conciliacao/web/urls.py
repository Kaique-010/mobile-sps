from django.urls import path

from .views.create import importar
from .views.detail import detalhe
from .views.list import listar


app_name = "conciliacao"

urlpatterns = [
    path("", listar, name="listar"),
    path("importar/", importar, name="importar"),
    path("<int:empresa>/<int:filial>/<int:numero>/", detalhe, name="detalhe"),
]
