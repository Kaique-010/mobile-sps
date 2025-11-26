from django.urls import path
from .Views.listView import TitulosReceberListView, autocomplete_clientes
from .Views.createView import TitulosReceberCreateView
from .Views.updateView import TitulosReceberUpdateView
from .Views.deleteView import TitulosReceberDeleteView
from .Views.autocompletes import autocomplete_cc

app_name = 'contas_a_receber_web'

# O slug é capturado no include do core/web_router.
urlpatterns = [
    path('', TitulosReceberListView.as_view(), name='titulos_receber_list'),
    path('novo/', TitulosReceberCreateView.as_view(), name='criar'),
    path('editar/<str:titu_titu>/<str:titu_parc>/', TitulosReceberUpdateView.as_view(), name='editar'),
    path('excluir/<str:titu_titu>/', TitulosReceberDeleteView.as_view(), name='excluir'),
    path('autocomplete/clientes/', autocomplete_clientes, name='autocomplete_clientes'),
    path('autocomplete/centrodecustos/', autocomplete_cc, name='autocomplete_centrodecustos'),
]