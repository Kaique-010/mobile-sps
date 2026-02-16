from django.urls import path
from .Views.listView import TitulosPagarListView, TitulosPagarParcelasListView, autocomplete_fornecedores
from .Views.createView import TitulosPagarCreateView, TitulosPagarParcelasCreateView
from .Views.updateView import TitulosPagarUpdateView
from .Views.deleteView import TitulosPagarDeleteView
from .Views.autocompletes import autocomplete_cc



app_name = 'contas_a_pagar_web'

# O slug é capturado no include do core/web_router.
urlpatterns = [
    path('', TitulosPagarListView.as_view(), name='titulos_pagar_list'),
    path('parcelas/', TitulosPagarParcelasListView.as_view(), name='parcelas_a_pagar_list'),
    path('parcelas/novo/', TitulosPagarParcelasCreateView.as_view(), name='parcelas_a_pagar_criar'),
    path('novo/', TitulosPagarCreateView.as_view(), name='criar'),
    path('editar/<str:titu_titu>/<str:titu_parc>/', TitulosPagarUpdateView.as_view(), name='editar'),
    path('excluir/<str:titu_titu>/', TitulosPagarDeleteView.as_view(), name='excluir'),
    path('autocomplete/fornecedores/', autocomplete_fornecedores, name='autocomplete_fornecedores'),
    path('autocomplete/centrodecustos/', autocomplete_cc, name='autocomplete_centrodecustos'),
]
