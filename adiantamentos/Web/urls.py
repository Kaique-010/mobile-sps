from django.urls import path
from .Views.listView import AdiantamentosListView
from .Views.createView import AdiantamentosCreateView
from .Views.updateView import AdiantamentosUpdateView
from .Views.deleteView import AdiantamentosDeleteView
from .Views.autocompletes import autocomplete_entidades, autocomplete_bancos
from .Views.usosView import adiantamento_usos


app_name = 'adiantamentos_web'

urlpatterns = [
    path('', AdiantamentosListView.as_view(), name='adiantamentos_list'),
    path('novo/', AdiantamentosCreateView.as_view(), name='adiantamento_criar'),
    path(
        'editar/<int:adia_empr>/<int:adia_fili>/<int:adia_enti>/<int:adia_docu>/<str:adia_seri>/',
        AdiantamentosUpdateView.as_view(),
        name='adiantamento_editar',
    ),
    path(
        'excluir/<int:adia_empr>/<int:adia_fili>/<int:adia_enti>/<int:adia_docu>/<str:adia_seri>/<str:adia_tipo>/',
        AdiantamentosDeleteView.as_view(),
        name='adiantamento_excluir',
    ),
    path(
        'usos/<int:adia_empr>/<int:adia_fili>/<int:adia_enti>/<int:adia_docu>/<str:adia_seri>/<str:adia_tipo>/',
        adiantamento_usos,
        name='adiantamento_usos',
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
