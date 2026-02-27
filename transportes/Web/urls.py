from django.urls import path
from transportes.Web.Views.VeiculosList import VeiculosListView
from transportes.Web.Views.VeiculosCreate import VeiculosCreateView
from transportes.Web.Views.VeiculosUpdate import VeiculosUpdateView
from transportes.Web.Views.VeiculosDelete import VeiculosDeleteView
from transportes.Rest.Views.autocompletes import (
    autocomplete_transportadoras,
    autocomplete_marcas,
    autocomplete_centrodecustos,
    autocomplete_entidades
)

app_name = 'transportes'

urlpatterns = [
    # Veiculos
    path('veiculos/', VeiculosListView.as_view(), name='veiculos_lista'),
    path('veiculos/novo/', VeiculosCreateView.as_view(), name='veiculos_novo'),
    path('veiculos/editar/<int:tran>/<int:sequ>/', VeiculosUpdateView.as_view(), name='veiculos_editar'),
    path('veiculos/deletar/<int:tran>/<int:sequ>/', VeiculosDeleteView.as_view(), name='veiculos_deletar'),

    # Autocompletes
    path('autocomplete/transportadoras/', autocomplete_transportadoras, name='autocomplete_transportadoras'),
    path('autocomplete/marcas/', autocomplete_marcas, name='autocomplete_marcas'),
    path('autocomplete/centrodecustos/', autocomplete_centrodecustos, name='autocomplete_centrodecustos'),
    path('autocomplete/entidades/', autocomplete_entidades, name='autocomplete_entidades'),
]
