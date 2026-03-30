from django.urls import path
from GestaoObras.web.views.listar import listar_obras
from GestaoObras.web.views.criar import criar_obra
from GestaoObras.web.views.detalhe import detalhe_obra
from GestaoObras.web.views.etapas import listar_etapas, criar_etapa
from GestaoObras.web.views.etapas import editar_etapa
from GestaoObras.web.views.materiais import listar_materiais, criar_movimento_material
from GestaoObras.web.views.materiais import autocomplete_produtos
from GestaoObras.web.views.materiais import editar_movimento_material
from GestaoObras.web.views.financeiro import listar_financeiro, criar_lancamento_financeiro
from GestaoObras.web.views.financeiro import editar_lancamento_financeiro
from GestaoObras.web.views.processos import listar_processos, criar_processo
from GestaoObras.web.views.processos import editar_processo
from GestaoObras.web.views.status import alterar_status_obra

app_name = "gestaoobras"

urlpatterns = [
    path("obras/", listar_obras, name="obras_list"),
    path("obras/novo/", criar_obra, name="obras_create"),
    path("obras/<int:obra_id>/", detalhe_obra, name="obras_detail"),
    path("obras/<int:obra_id>/status/", alterar_status_obra, name="obras_status_update"),
    path("autocompletes/produtos/", autocomplete_produtos, name="obras_autocomplete_produtos"),
    path("obras/<int:obra_id>/etapas/", listar_etapas, name="obras_etapas_list"),
    path("obras/<int:obra_id>/etapas/novo/", criar_etapa, name="obras_etapas_create"),
    path("obras/<int:obra_id>/etapas/<int:etapa_id>/editar/", editar_etapa, name="obras_etapas_edit"),
    path("obras/<int:obra_id>/materiais/", listar_materiais, name="obras_materiais_list"),
    path("obras/<int:obra_id>/materiais/novo/", criar_movimento_material, name="obras_materiais_create"),
    path("obras/<int:obra_id>/materiais/<int:movimento_id>/editar/", editar_movimento_material, name="obras_materiais_edit"),
    path("obras/<int:obra_id>/financeiro/", listar_financeiro, name="obras_financeiro_list"),
    path("obras/<int:obra_id>/financeiro/novo/", criar_lancamento_financeiro, name="obras_financeiro_create"),
    path("obras/<int:obra_id>/financeiro/<int:lancamento_id>/editar/", editar_lancamento_financeiro, name="obras_financeiro_edit"),
    path("obras/<int:obra_id>/processos/", listar_processos, name="obras_processos_list"),
    path("obras/<int:obra_id>/processos/novo/", criar_processo, name="obras_processos_create"),
    path("obras/<int:obra_id>/processos/<int:processo_id>/editar/", editar_processo, name="obras_processos_edit"),
]
