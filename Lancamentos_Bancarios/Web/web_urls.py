from django.urls import path

from .Views.dashboard import DashboardView
from .Views.list import LancamentosListView
from .Views.create import LancamentoEntradaCreateView, LancamentoSaidaCreateView
from .Views.update import LancamentoEntradaUpdateView, LancamentoSaidaUpdateView
from .Views.delete import LancamentoEntradaDeleteView, LancamentoSaidaDeleteView
from .Views.autocompletes import autocomplete_bancos, autocomplete_centrosdecustos, autocomplete_entidades

app_name = 'lancamentos_bancarios_web'

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('lancamentos/', LancamentosListView.as_view(), name='lancamentos_list'),
    path('lancamentos/entrada/novo/', LancamentoEntradaCreateView.as_view(), name='lancamento_entrada_criar'),
    path('lancamentos/saida/novo/', LancamentoSaidaCreateView.as_view(), name='lancamento_saida_criar'),
    path('lancamentos/entrada/<int:laba_ctrl>/editar/', LancamentoEntradaUpdateView.as_view(), name='lancamento_entrada_editar'),
    path('lancamentos/saida/<int:laba_ctrl>/editar/', LancamentoSaidaUpdateView.as_view(), name='lancamento_saida_editar'),
    path('lancamentos/entrada/<int:laba_ctrl>/excluir/', LancamentoEntradaDeleteView.as_view(), name='lancamento_entrada_excluir'),
    path('lancamentos/saida/<int:laba_ctrl>/excluir/', LancamentoSaidaDeleteView.as_view(), name='lancamento_saida_excluir'),
    path("autocomplete/bancos/", autocomplete_bancos, name="autocomplete_bancos"),
    path("autocomplete/centrodecustos/", autocomplete_centrosdecustos, name="autocomplete_centrosdecustos"),
    path("autocomplete/entidades/", autocomplete_entidades, name="autocomplete_entidades"),
]
