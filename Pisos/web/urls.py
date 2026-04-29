from django.urls import path
from Pisos.web.views.listar import listar_pedidos_pisos
from Pisos.web.views.criar import criar_pedido_pisos
from Pisos.web.views.editar import editar_pedido_pisos
from Pisos.web.views.visualizar import visualizar_pedido_pisos
from Pisos.web.views.orcamentos_criar import criar_orcamento_pisos
from Pisos.web.views.orcamentos_editar import editar_orcamento_pisos
from Pisos.web.views.orcamentos_exportar import exportar_orcamento_pedido
from Pisos.web.views.orcamentos_listar import listar_orcamentos_pisos
from Pisos.web.views.orcamentos_visualizar import visualizar_orcamento_pisos
from Pisos.web.views.calcular_item_view import api_calcular_item

from Pisos.web.views.utils import autocomplete_clientes, autocomplete_vendedores, autocomplete_produtos

app_name = "PisosWeb"

urlpatterns = [
    path("pedidos-pisos/", listar_pedidos_pisos, name="pedidos_pisos_listar"),
    path("pedidos-pisos/novo/", criar_pedido_pisos, name="pedidos_pisos_criar"),
    path("pedidos-pisos/<int:pk>/", visualizar_pedido_pisos, name="pedidos_pisos_visualizar"),
    path("pedidos-pisos/<int:pk>/editar/", editar_pedido_pisos, name="pedidos_pisos_editar"),
    path("autocompletes/clientes/", autocomplete_clientes, name="autocomplete_clientes"),
    path("autocompletes/vendedores/", autocomplete_vendedores, name="autocomplete_vendedores"),
    path("autocompletes/produtos/", autocomplete_produtos, name="autocomplete_produtos"),
    path("orcamentos-pisos/", listar_orcamentos_pisos, name="orcamentos_pisos_listar"),
    path("orcamentos-pisos/novo/", criar_orcamento_pisos, name="orcamentos_pisos_criar"),
    path("orcamentos-pisos/<int:pk>/", visualizar_orcamento_pisos, name="orcamentos_pisos_visualizar"),
    path("orcamentos-pisos/<int:pk>/editar/", editar_orcamento_pisos, name="orcamentos_pisos_editar"),
    path("orcamentos-pisos/<int:numero>/exportar/", exportar_orcamento_pedido, name="orcamentos_pisos_exportar"),
    path("calcular-item/", api_calcular_item, name="api_calcular_item"),
]
