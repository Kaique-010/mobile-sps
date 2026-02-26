from django.urls import path
from .Views.listView import BensptrListView
from .Views.createView import BensCreateView
from .Views.updateView import BensUpdateView
from .Views.deleteView import BensDeleteView
from .Views.gruposView import (
    GrupobensListView, GrupobensCreateView, 
    GrupobensUpdateView, GrupobensDeleteView
)
from .Views.motivosView import (
    MotivosptrListView, MotivosptrCreateView, 
    MotivosptrUpdateView, MotivosptrDeleteView
)

app_name = 'bens_web'

urlpatterns = [
    # Rotas de Bens
    path('', BensptrListView.as_view(), name='bens_list'),
    path('novo/', BensCreateView.as_view(), name='bens_criar'),
    path(
        'editar/<int:bens_empr>/<int:bens_fili>/<str:bens_codi>/',
        BensUpdateView.as_view(),
        name='bens_editar',
    ),
    path(
        'excluir/<int:bens_empr>/<int:bens_fili>/<str:bens_codi>/',
        BensDeleteView.as_view(),
        name='bens_excluir',
    ),

    # Rotas de Grupos
    path('grupos/', GrupobensListView.as_view(), name='grupo_list'),
    path('grupos/novo/', GrupobensCreateView.as_view(), name='grupo_criar'),
    path(
        'grupos/editar/<int:grup_empr>/<str:grup_codi>/',
        GrupobensUpdateView.as_view(),
        name='grupo_editar',
    ),
    path(
        'grupos/excluir/<int:grup_empr>/<str:grup_codi>/',
        GrupobensDeleteView.as_view(),
        name='grupo_excluir',
    ),

    # Rotas de Motivos
    path('motivos/', MotivosptrListView.as_view(), name='motivo_list'),
    path('motivos/novo/', MotivosptrCreateView.as_view(), name='motivo_criar'),
    path(
        'motivos/editar/<str:moti_codi>/',
        MotivosptrUpdateView.as_view(),
        name='motivo_editar',
    ),
    path(
        'motivos/excluir/<str:moti_codi>/',
        MotivosptrDeleteView.as_view(),
        name='motivo_excluir',
    ),
]
