from django.urls import path
from transportes.views import web, api
from transportes.views import regras
from transportes.Web.Views.VeiculosList import VeiculosListView
from transportes.Web.Views.VeiculosCreate import VeiculosCreateView
from transportes.Web.Views.VeiculosUpdate import VeiculosUpdateView
from transportes.Web.Views.VeiculosDelete import VeiculosDeleteView
from transportes.Web.Views.BombasList import BombasListView
from transportes.Web.Views.BombasCreate import BombasCreateView
from transportes.Web.Views.BombasUpdate import BombasUpdateView
from transportes.Web.Views.BombasDelete import BombasDeleteView
from transportes.Web.Views.AbastecimentosList import AbastecimentosListView
from transportes.Web.Views.AbastecimentosCreate import AbastecimentosCreateView
from transportes.Web.Views.AbastecimentosUpdate import AbastecimentosUpdateView
from transportes.Web.Views.AbastecimentosDelete import AbastecimentosDeleteView
from transportes.Web.Views.LancamentoCustosList import LancamentoCustosListView
from transportes.Web.Views.LancamentoCustosCreate import LancamentoCustosCreateView
from transportes.Web.Views.LancamentoCustosUpdate import LancamentoCustosUpdateView
from transportes.Web.Views.LancamentoCustosDelete import LancamentoCustosDeleteView
from transportes.Web.Views.BombasSaldosList import BombasSaldosListView
from transportes.Web.Views.BombasSaldosCreate import BombasSaldosCreateView
from transportes.Web.Views.BombasSaldosUpdate import BombasSaldosUpdateView
from transportes.Web.Views.BombasSaldosDelete import BombasSaldosDeleteView
from transportes.Web.Views.DashboardManutencoes import DashboardManutencoesView
from transportes.Rest.Views.autocompletes import autocomplete_transportadoras, autocomplete_marcas, autocomplete_centrodecustos, autocomplete_entidades, autocomplete_veiculos, autocomplete_bombas, autocomplete_combustiveis, get_entidade_detalhes
from transportes.Web.Views.TranspMotoList import TranspMotoListView
from transportes.Web.Views.TranspMotoUpdate import TranspMotoUpdateView
from transportes.Rest.Views.transp_moto import TranspMotoListApiView, TranspMotoUpdateApiView
from transportes.Rest.Views.bombas import BombasListApiView, BombasDetailApiView
from transportes.Rest.Views.abastecimentos import AbastecimentoViewSet
from transportes.Rest.Views.lancamento_custos import LancamentoCustosViewSet
from transportes.Rest.Views.abastecimentos_resumo import abastecimentos_resumo
from transportes.Rest.Views.bombas_saldos import BombasSaldosViewSet



app_name = 'transportes'

urlpatterns = [
    path('manutencoes/', DashboardManutencoesView.as_view(), name='manutencoes_dashboard'),
    # Veículos
    path('veiculos/', VeiculosListView.as_view(), name='veiculos_lista'),
    path('veiculos/novo/', VeiculosCreateView.as_view(), name='veiculos_novo'),
    path('veiculos/<int:tran>/<int:sequ>/editar/', VeiculosUpdateView.as_view(), name='veiculos_editar'),
    path('veiculos/<int:tran>/<int:sequ>/excluir/', VeiculosDeleteView.as_view(), name='veiculos_deletar'),
    
    # Transportadoras Motos
    path('transportadoras_motoristas/', TranspMotoListView.as_view(), name='transportadoras_motoristas_lista'),
    path('transportadoras_motoristas/<int:enti_clie>/editar/', TranspMotoUpdateView.as_view(), name='transportadoras_motoristas_editar'),
    path('api/transportadoras_motoristas/', TranspMotoListApiView.as_view(), name='transportadoras_motoristas_api_lista'),
    path('api/transportadoras_motoristas/<int:enti_clie>/', TranspMotoUpdateApiView.as_view(), name='transportadoras_motoristas_api_editar'),
    
    # Bombas
    path('bombas/', BombasListView.as_view(), name='bombas_lista'),
    path('bombas/novo/', BombasCreateView.as_view(), name='bombas_novo'),
    path('bombas/<str:bomb_codi>/editar/', BombasUpdateView.as_view(), name='bombas_editar'),
    path('bombas/<str:bomb_codi>/excluir/', BombasDeleteView.as_view(), name='bombas_deletar'),
    path('api/bombas/', BombasListApiView.as_view(), name='bombas_api_lista'),
    path('api/bombas/<str:bomb_codi>/', BombasDetailApiView.as_view(), name='bombas_api_detalhe'),

    # Abastecimentos
    path('abastecimentos/', AbastecimentosListView.as_view(), name='abastecimentos_lista'),
    path('abastecimentos/novo/', AbastecimentosCreateView.as_view(), name='abastecimentos_novo'),
    path('abastecimentos/<int:abas_ctrl>/editar/', AbastecimentosUpdateView.as_view(), name='abastecimentos_editar'),
    path('abastecimentos/<int:abas_ctrl>/excluir/', AbastecimentosDeleteView.as_view(), name='abastecimentos_deletar'),
    path(
        'api/abastecimentos/',
        AbastecimentoViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='abastecimentos_api_lista',
    ),
    path(
        'api/abastecimentos/<int:pk>/',
        AbastecimentoViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='abastecimentos_api_detalhe',
    ),
    path('api/abastecimentos/resumo/', abastecimentos_resumo, name='abastecimentos_api_resumo'),

    # Lançamentos de Custos
    path('lancamento_custos/', LancamentoCustosListView.as_view(), name='lancamento_custos_lista'),
    path('lancamento_custos/novo/', LancamentoCustosCreateView.as_view(), name='lancamento_custos_novo'),
    path('lancamento_custos/<int:lacu_ctrl>/editar/', LancamentoCustosUpdateView.as_view(), name='lancamento_custos_editar'),
    path('lancamento_custos/<int:lacu_ctrl>/excluir/', LancamentoCustosDeleteView.as_view(), name='lancamento_custos_deletar'),
    path(
        'api/lancamento_custos/',
        LancamentoCustosViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='lancamento_custos_api_lista',
    ),
    path(
        'api/lancamento_custos/<int:pk>/',
        LancamentoCustosViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='lancamento_custos_api_detalhe',
    ),

    # Movimentação por Bomba
    path('bombas_saldos/', BombasSaldosListView.as_view(), name='bombas_saldos_lista'),
    path('bombas_saldos/novo/', BombasSaldosCreateView.as_view(), name='bombas_saldos_novo'),
    path('bombas_saldos/<int:bomb_id>/editar/', BombasSaldosUpdateView.as_view(), name='bombas_saldos_editar'),
    path('bombas_saldos/<int:bomb_id>/excluir/', BombasSaldosDeleteView.as_view(), name='bombas_saldos_deletar'),
    path(
        'api/bombas_saldos/',
        BombasSaldosViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='bombas_saldos_api_lista',
    ),
    path(
        'api/bombas_saldos/<int:pk>/',
        BombasSaldosViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='bombas_saldos_api_detalhe',
    ),


    # Listagem
    path('ctes/', web.CteListView.as_view(), name='cte_list'),
    path('ctes/novo/', web.CteCreateView.as_view(), name='cte_create'),

    # MDF-e
    path('mdfes/', web.MdfeListView.as_view(), name='mdfe_list'),
    path('mdfes/novo/', web.MdfeCreateView.as_view(), name='mdfe_create'),
    path('mdfes/<int:pk>/dados/', web.MdfeDadosView.as_view(), name='mdfe_dados'),
    path('mdfes/<int:pk>/documentos/', web.MdfeDocumentosView.as_view(), name='mdfe_documentos'),
    path('mdfes/<int:pk>/antt/', web.MdfeAnttView.as_view(), name='mdfe_antt'),
    path('mdfes/<int:pk>/contratantes/', web.MdfeContratantesView.as_view(), name='mdfe_contratantes'),
    path('mdfes/<int:pk>/seguro/', web.MdfeSeguroView.as_view(), name='mdfe_seguro'),
    path('mdfes/<int:pk>/gerar-xml/', web.MdfeGerarXmlView.as_view(), name='mdfe_gerar_xml'),
    path('mdfes/<int:pk>/imprimir/', web.MdfeImprimirDamdfeView.as_view(), name='mdfe_imprimir'),
    path('mdfes/<int:pk>/encerrar/', web.MdfeEncerrarView.as_view(), name='mdfe_encerrar'),
    
    # Abas de Edição
    path('ctes/<str:pk>/emissao/', web.CteEmissaoView.as_view(), name='cte_emissao'),
    path('ctes/<str:pk>/tipo/', web.CteTipoView.as_view(), name='cte_tipo'),
    path('ctes/<str:pk>/rota/', web.CteRotaView.as_view(), name='cte_rota'),
    path('ctes/<str:pk>/seguro/', web.CteSeguroView.as_view(), name='cte_seguro'),
    path('ctes/<str:pk>/carga/', web.CteCargaView.as_view(), name='cte_carga'),
    path('ctes/<str:pk>/documentos/', web.CteDocumentoView.as_view(), name='cte_documento'),
    path('ctes/<str:pk>/tributacao/', web.CteTributacaoView.as_view(), name='cte_tributacao'),
    
    # Ações
    path('ctes/<str:pk>/excluir/', web.CteDeleteView.as_view(), name='cte_delete'),
    path('ctes/<str:pk>/emitir/', web.CteEmitirView.as_view(), name='cte_emitir'),
    path('ctes/<str:pk>/consultar-recibo/', web.CteConsultarReciboView.as_view(), name='cte_consultar_recibo'),
    path('ctes/<str:pk>/imprimir/', web.CteImprimirDacteView.as_view(), name='cte_imprimir'),

    # APIs para AJAX nos Templates
    path('api/ctes/<str:pk>/rota-info/', api.get_cte_rota_info, name='api_cte_rota_info'),
    path('api/ctes/<str:pk>/calcular-impostos/', api.calcular_impostos_cte, name='api_cte_calcular_impostos'),
    path('api/mdfes/proximo-numero/', api.get_mdfe_proximo_numero, name='api_mdfe_proximo_numero'),

    # Regras ICMS
    path('regras/', regras.RegraICMSListView.as_view(), name='regra_list'),
    path('regras/nova/', regras.RegraICMSCreateView.as_view(), name='regra_create'),
    path('regras/<int:pk>/editar/', regras.RegraICMSUpdateView.as_view(), name='regra_update'),
    path('regras/<int:pk>/excluir/', regras.RegraICMSDeleteView.as_view(), name='regra_delete'),
    
    # Autocompletes
    path('autocomplete/transportadoras/', autocomplete_transportadoras, name='autocomplete_transportadoras'),
    path('autocomplete/marcas/', autocomplete_marcas, name='autocomplete_marcas'),
    path('autocomplete/centrodecustos/', autocomplete_centrodecustos, name='autocomplete_centrodecustos'),
    path('autocomplete/entidades/', autocomplete_entidades, name='autocomplete_entidades'),
    path('autocomplete/veiculos/', autocomplete_veiculos, name='autocomplete_veiculos'),
    path('autocomplete/bombas/', autocomplete_bombas, name='autocomplete_bombas'),
    path('autocomplete/combustiveis/', autocomplete_combustiveis, name='autocomplete_combustiveis'),
    path('api/entidade/detalhes/', get_entidade_detalhes, name='api_entidade_detalhes'),
]
