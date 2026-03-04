from django.urls import path
from transportes.views import web
from transportes.Web.Views.VeiculosList import VeiculosListView
from transportes.Web.Views.VeiculosCreate import VeiculosCreateView
from transportes.Web.Views.VeiculosUpdate import VeiculosUpdateView
from transportes.Web.Views.VeiculosDelete import VeiculosDeleteView
from transportes.Rest.Views.autocompletes import autocomplete_transportadoras, autocomplete_marcas, autocomplete_centrodecustos, autocomplete_entidades, autocomplete_veiculos



app_name = 'transportes'

urlpatterns = [
    # Veículos
    path('veiculos/', VeiculosListView.as_view(), name='veiculos_lista'),
    path('veiculos/novo/', VeiculosCreateView.as_view(), name='veiculos_novo'),
    path('veiculos/<int:tran>/<int:sequ>/editar/', VeiculosUpdateView.as_view(), name='veiculos_editar'),
    path('veiculos/<int:tran>/<int:sequ>/excluir/', VeiculosDeleteView.as_view(), name='veiculos_deletar'),

    # Listagem
    path('ctes/', web.CteListView.as_view(), name='cte_list'),
    path('ctes/novo/', web.CteCreateView.as_view(), name='cte_create'),
    
    # Abas de Edição
    path('ctes/<str:pk>/emissao/', web.CteEmissaoView.as_view(), name='cte_emissao'),
    path('ctes/<str:pk>/tipo/', web.CteTipoView.as_view(), name='cte_tipo'),
    path('ctes/<str:pk>/rota/', web.CteRotaView.as_view(), name='cte_rota'),
    path('ctes/<str:pk>/seguro/', web.CteSeguroView.as_view(), name='cte_seguro'),
    path('ctes/<str:pk>/carga/', web.CteCargaView.as_view(), name='cte_carga'),
    path('ctes/<str:pk>/tributacao/', web.CteTributacaoView.as_view(), name='cte_tributacao'),
    
    # Ações
    path('ctes/<str:pk>/excluir/', web.CteDeleteView.as_view(), name='cte_delete'),
    path('ctes/<str:pk>/emitir/', web.CteEmitirView.as_view(), name='cte_emitir'),
    path('ctes/<str:pk>/consultar-recibo/', web.CteConsultarReciboView.as_view(), name='cte_consultar_recibo'),
    
        # Autocompletes
    path('autocomplete/transportadoras/', autocomplete_transportadoras, name='autocomplete_transportadoras'),
    path('autocomplete/marcas/', autocomplete_marcas, name='autocomplete_marcas'),
    path('autocomplete/centrodecustos/', autocomplete_centrodecustos, name='autocomplete_centrodecustos'),
    path('autocomplete/entidades/', autocomplete_entidades, name='autocomplete_entidades'),
    path('autocomplete/veiculos/', autocomplete_veiculos, name='autocomplete_veiculos'),
]
