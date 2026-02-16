from django.urls import path
from .Views.listView import TitulosReceberListView, TitulosReceberParcelasListView, autocomplete_clientes
from .Views.createView import TitulosReceberCreateView, TitulosReceberParcelasCreateView
from .Views.updateView import TitulosReceberUpdateView
from .Views.deleteView import TitulosReceberDeleteView
from .Views.autocompletes import autocomplete_cc, autocomplete_bancos

app_name = 'contas_a_receber_web'

# O slug é capturado no include do core/web_router.
urlpatterns = [
    path('', TitulosReceberListView.as_view(), name='titulos_receber_list'),
    path('parcelas/', TitulosReceberParcelasListView.as_view(), name='parcelas_a_receber_list'),
    path('parcelas/novo/', TitulosReceberParcelasCreateView.as_view(), name='parcelas_a_receber_criar'),
    path('novo/', TitulosReceberCreateView.as_view(), name='criar'),
    path('editar/<str:titu_titu>/<str:titu_parc>/', TitulosReceberUpdateView.as_view(), name='editar'),
    path('excluir/<str:titu_titu>/', TitulosReceberDeleteView.as_view(), name='excluir'),
    path('autocomplete/clientes/', autocomplete_clientes, name='autocomplete_clientes'),
    path('autocomplete/centrodecustos/', autocomplete_cc, name='autocomplete_centrodecustos'),
    path('autocomplete/bancos/', autocomplete_bancos, name='autocomplete_bancos'),
]
