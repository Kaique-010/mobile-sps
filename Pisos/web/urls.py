from django.urls import path
from Pisos.web.views.listar import PedidopisosListView, ExportarPedidosView
from Pisos.web.views.criar import criar_pedido_pisos
from Pisos.web.views.editar import editar_pedido_pisos
from Pisos.web.views.visualizar import visualizar_pedido_pisos
from Pisos.web.views.orcamentos_criar import criar_orcamento_pisos
from Pisos.web.views.orcamentos_editar import editar_orcamento_pisos
from Pisos.web.views.orcamentos_exportar import exportar_orcamento_pedido
from Pisos.web.views.orcamentos_listar import OrcamentoPisosListView, ExportarOrcamentosView
from Pisos.web.views.orcamentos_visualizar import visualizar_orcamento_pisos
from Pisos.web.views.calcular_item_view import api_calcular_item
from Pisos.web.views.impressao import imprimir_pedido_pisos, imprimir_orcamento_pisos
from Pisos.web.views.arquivos import download_pedido_pisos_arquivo, excluir_pedido_pisos_arquivo, upload_pedido_pisos_arquivo
from Pisos.web.views.painel_pedidos_view import modal_painel_pedidos
from Pisos.web.views.utils import autocomplete_clientes, autocomplete_vendedores, autocomplete_produtos
from Pisos.web.views.comissao_view import ComissaoVendedorView, ExportarComissoesView
from Pisos.web.views.workflow_pedido import PedidoWorkflowAjaxView
from Pisos.web.views.romaneio_entrega import RomaneioEntregaAjaxView
from Pisos.web.views.pedido_emitir_nfe_view import PedidoPisosEmitirNFeView
from Pisos.web.views.status_pisos_views import (
    StatusPisosListView,
    StatusPisosCreateView,
    StatusPisosUpdateView,
    StatusPisosDeleteView,
    criar_status_padrao_view,
)
from Pisos.web.views.status_workflow_views import alterar_status_pedido_pisos, alterar_status_orcamento_pisos
from Pisos.web.views.views_rentabilidade import rentabilidade_documento


app_name = "PisosWeb"

urlpatterns = [
    path("pedidos-pisos/", PedidopisosListView.as_view(), name="pedidos_pisos_listar"),
    path("pedidos-pisos/novo/", criar_pedido_pisos, name="pedidos_pisos_criar"),
    path("pedidos-pisos/<int:pk>/", visualizar_pedido_pisos, name="pedidos_pisos_visualizar"),
    path("pedidos-pisos/<int:pk>/editar/", editar_pedido_pisos, name="pedidos_pisos_editar"),
    path("pedidos-pisos/<int:pk>/imprimir/", imprimir_pedido_pisos, name="pedidos_pisos_imprimir"),
    path("pedidos-pisos/exportar/", ExportarPedidosView.as_view(), name="pedidos_pisos_exportar"),
    path("pedidos-pisos/<int:pk>/arquivos/upload/", upload_pedido_pisos_arquivo, name="pedidos_pisos_arquivos_upload"),
    path("pedidos-pisos/<int:pk>/arquivos/<int:codigo>/", download_pedido_pisos_arquivo, name="pedidos_pisos_arquivos_download"),
    path(
        "pedidos-pisos/<int:pk>/arquivos/<int:codigo>/excluir/",
        excluir_pedido_pisos_arquivo,
        name="pedidos_pisos_arquivos_excluir",
    ),
    path("autocompletes/clientes/", autocomplete_clientes, name="autocomplete_clientes"),
    path("autocompletes/vendedores/", autocomplete_vendedores, name="autocomplete_vendedores"),
    path("autocompletes/produtos/", autocomplete_produtos, name="autocomplete_produtos"),
    path("orcamentos-pisos/", OrcamentoPisosListView.as_view(), name="orcamentos_pisos_listar"),
    path("orcamentos-pisos/novo/", criar_orcamento_pisos, name="orcamentos_pisos_criar"),
    path("orcamentos-pisos/<int:pk>/", visualizar_orcamento_pisos, name="orcamentos_pisos_visualizar"),
    path("orcamentos-pisos/<int:pk>/editar/", editar_orcamento_pisos, name="orcamentos_pisos_editar"),
    path("orcamentos-pisos/<int:pk>/imprimir/", imprimir_orcamento_pisos, name="orcamentos_pisos_imprimir"),
    path("orcamentos-pisos/<int:numero>/exportar/", exportar_orcamento_pedido, name="orcamentos_pisos_exportar"),
    path("orcamentos-pisos/exportar/", ExportarOrcamentosView.as_view(), name="orcamentos_pisos_listar_exportar"),
    path("calcular-item/", api_calcular_item, name="api_calcular_item"),
    path("comissoes-vendedores/", ComissaoVendedorView.as_view(), name="comissoes_vendedores"),
    path("comissoes-vendedores/exportar/", ExportarComissoesView.as_view(), name="comissoes_vendedores_exportar"),
    path("pedidos-pisos/<int:pk>/workflow/", PedidoWorkflowAjaxView.as_view(), name="pedidos_pisos_workflow_ajax"),
    path(
        "pedidos-pisos/<int:pk>/romaneio-entrega/",
        RomaneioEntregaAjaxView.as_view(),
        name="pedidos_pisos_romaneio_entrega_ajax",
    ),
    path(
        "pedidos-pisos/<int:pk>/emitir-nfe/",
        PedidoPisosEmitirNFeView.as_view(),
        name="pedidos_pisos_emitir_nfe",
    ),

     path(
        "status-pisos/",
        StatusPisosListView.as_view(),
        name="status_pisos_listar"
    ),
    path(
        "status-pisos/novo/",
        StatusPisosCreateView.as_view(),
        name="status_pisos_criar"
    ),
    path(
        "status-pisos/<int:pk>/editar/",
        StatusPisosUpdateView.as_view(),
        name="status_pisos_editar"
    ),
    path(
        "status-pisos/<int:pk>/excluir/",
        StatusPisosDeleteView.as_view(),
        name="status_pisos_excluir"
    ),
    path(
        "status-pisos/criar-padrao/",
        criar_status_padrao_view,
        name="status_pisos_criar_padrao"
    ),
    # Pisos/urls.py

    path(
        "pedidos-pisos/<int:pk>/alterar-status/",
        alterar_status_pedido_pisos,
        name="pedidos_pisos_alterar_status",
    ),

    path(
        "orcamentos-pisos/<int:pk>/alterar-status/",
        alterar_status_orcamento_pisos,
        name="orcamentos_pisos_alterar_status",
    ),
    path(
        'painel-pedidos/',
        modal_painel_pedidos,
        name='modal_painel_pedidos'
    ),
    path(
    "rentabilidade/<str:tipo>/<int:numero>/",
    rentabilidade_documento,
    name="rentabilidade_documento",
),
]
