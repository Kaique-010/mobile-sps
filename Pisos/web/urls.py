from django.urls import path
from Pisos.web.views.listar import listar_pedidos_pisos
from Pisos.web.views.criar import criar_pedido_pisos
from Pisos.web.views.editar import editar_pedido_pisos
from Pisos.web.views.visualizar import visualizar_pedido_pisos
from Pisos.web.views.utils import autocomplete_clientes, autocomplete_vendedores

app_name = "PisosWeb"

urlpatterns = [
    path("pedidos-pisos/", listar_pedidos_pisos, name="pedidos_pisos_listar"),
    path("pedidos-pisos/novo/", criar_pedido_pisos, name="pedidos_pisos_criar"),
    path("pedidos-pisos/<int:pk>/", visualizar_pedido_pisos, name="pedidos_pisos_visualizar"),
    path("pedidos-pisos/<int:pk>/editar/", editar_pedido_pisos, name="pedidos_pisos_editar"),
    path("autocompletes/clientes/", autocomplete_clientes, name="autocomplete_clientes"),
    path("autocompletes/vendedores/", autocomplete_vendedores, name="autocomplete_vendedores"),
]
