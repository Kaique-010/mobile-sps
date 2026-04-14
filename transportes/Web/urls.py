from django.urls import path
from transportes.views import web, api
from transportes.views import regras
from transportes.Web.Views.VeiculosList import VeiculosListView
from transportes.Web.Views.VeiculosCreate import VeiculosCreateView
from transportes.Web.Views.VeiculosUpdate import VeiculosUpdateView
from transportes.Web.Views.VeiculosDelete import VeiculosDeleteView
from transportes.Rest.Views.autocompletes import autocomplete_transportadoras, autocomplete_marcas, autocomplete_centrodecustos, autocomplete_entidades, autocomplete_veiculos, get_entidade_detalhes
from transportes.Web.Views.TranspMotoList import TranspMotoListView
#from transportes.Web.Views.TranspMotoCreate import TranspMotoCreateView
#from transportes.Web.Views.TranspMotoUpdate import TranspMotoUpdateView
#from transportes.Web.Views.TranspMotoDelete import TranspMotoDeleteView



app_name = 'transportes'

urlpatterns = [
    # Veículos
    path('veiculos/', VeiculosListView.as_view(), name='veiculos_lista'),
    path('veiculos/novo/', VeiculosCreateView.as_view(), name='veiculos_novo'),
    path('veiculos/<int:tran>/<int:sequ>/editar/', VeiculosUpdateView.as_view(), name='veiculos_editar'),
    path('veiculos/<int:tran>/<int:sequ>/excluir/', VeiculosDeleteView.as_view(), name='veiculos_deletar'),
    
    # Transportadoras Motos
    path('transportadoras_motoristas/', TranspMotoListView.as_view(), name='transportadoras_motoristas_lista'),
    #path('transportadoras_motoristas/novo/', TranspMotoCreateView.as_view(), name='transportadoras_motoristas_novo'),
    #path('transportadoras_motoristas/<int:tran>/<int:sequ>/editar/', TranspMotoUpdateView.as_view(), name='transportadoras_motoristas_editar'),
    #path('transportadoras_motoristas/<int:tran>/<int:sequ>/excluir/', TranspMotoDeleteView.as_view(), name='transportadoras_motoristas_deletar'),



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
    path('api/entidade/detalhes/', get_entidade_detalhes, name='api_entidade_detalhes'),
]
