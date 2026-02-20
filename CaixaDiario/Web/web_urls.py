from django.urls import path
from . import web_views

app_name = "CaixaDiarioWeb"

urlpatterns = [
    path("", web_views.CaixaDashboardView.as_view(), name="caixa_dashboard"),
    path("geral/", web_views.CaixaGeralPageView.as_view(), name="caixa_geral"),
    path("venda/", web_views.CaixaAbaVendaPageView.as_view(), name="caixa_venda"),
    path("produtos/", web_views.CaixaAbaProdutosPageView.as_view(), name="caixa_produtos"),
    path("processamento/", web_views.CaixaAbaProcessamentoPageView.as_view(), name="caixa_processamento"),
    path("extrato/", web_views.CaixaAbaExtratoPageView.as_view(), name="caixa_extrato"),
    path("origens/", web_views.origens_caixa, name="origens_caixa"),
    path("caixa/proximo-numero/", web_views.proximo_caixa_numero, name="proximo_caixa_numero"),
    path("caixa/resumo/", web_views.caixa_resumo, name="caixa_resumo"),
    path("caixa/lancamento/", web_views.lancamento, name="caixa_lancamento"),
    path("autocomplete/clientes/", web_views.autocomplete_clientes, name="autocomplete_clientes"),
    path("autocomplete/vendedores/", web_views.autocomplete_vendedores, name="autocomplete_vendedores"),
    path("autocomplete/produtos/", web_views.autocomplete_produtos, name="autocomplete_produtos"),
    path("caixas/abertos/", web_views.caixas_abertos, name="caixas_abertos"),
    path("venda/iniciar/", web_views.venda_iniciar, name="venda_iniciar"),
    path("venda/adicionar-item/", web_views.venda_adicionar_item, name="venda_adicionar_item"),
    path("venda/atualizar-item/", web_views.venda_atualizar_item, name="venda_atualizar_item"),
    path("venda/remover-item/", web_views.venda_remover_item, name="venda_remover_item"),
    path("venda/processar-pagamento/", web_views.venda_processar_pagamento, name="venda_processar_pagamento"),
    path("venda/status/", web_views.venda_status, name="venda_status"),
    path("venda/finalizar/", web_views.venda_finalizar, name="venda_finalizar"),
    path("venda/emitir/", web_views.venda_emitir, name="venda_emitir"),
    path("venda/extrato/", web_views.venda_extrato, name="venda_extrato"),
]
