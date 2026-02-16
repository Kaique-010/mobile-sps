from django.urls import path
from .Views.listView import AdiantamentosListView
from .Views.createView import AdiantamentosCreateView
from .Views.updateView import AdiantamentosUpdateView
from .Views.deleteView import AdiantamentosDeleteView
from .Views.autocompletes import autocomplete_entidades, autocomplete_bancos


app_name = 'adiantamentos_web'

urlpatterns = [
    path('', AdiantamentosListView.as_view(), name='adiantamentos_list'),
    path('novo/', AdiantamentosCreateView.as_view(), name='adiantamento_criar'),
    path(
        'editar/<int:adia_enti>/<int:adia_docu>/<str:adia_seri>/',
        AdiantamentosUpdateView.as_view(),
        name='adiantamento_editar',
    ),
    path(
        'excluir/<int:adia_enti>/<int:adia_docu>/<str:adia_seri>/',
        AdiantamentosDeleteView.as_view(),
        name='adiantamento_excluir',
    ),
    path(
        'autocomplete/entidades/',
        autocomplete_entidades,
        name='autocomplete_entidades',
    ),
    path(
        'autocomplete/bancos/',
        autocomplete_bancos,
        name='autocomplete_bancos',
    ),
]
