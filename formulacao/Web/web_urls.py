from django.urls import path

from .Views.formula_create_view import FormulaCreateView
from .Views.formula_edit_view import FormulaEditView
from .Views.formula_list_view import FormulaListView, autocomplete_produtos
from .Views.ordem_create_view import OrdemProducaoCreateView
from .Views.ordem_edit_view import OrdemProducaoEditView
from .Views.ordem_executar_view import OrdemProducaoExecutarView
from .Views.ordem_list_view import OrdemProducaoListView

app_name = "FormulacaoWeb"

urlpatterns = [
    path("formulas/", FormulaListView.as_view(), name="formula_list"),
    path("formulas/nova/", FormulaCreateView.as_view(), name="formula_create"),
    path("formulas/<int:pk>/", FormulaEditView.as_view(), name="formula_edit"),
    path("autocomplete/produtos/", autocomplete_produtos, name="autocomplete_produtos"),
    path("ordens/", OrdemProducaoListView.as_view(), name="ordem_list"),
    path("ordens/nova/", OrdemProducaoCreateView.as_view(), name="ordem_create"),
    path("ordens/<int:pk>/editar/", OrdemProducaoEditView.as_view(), name="ordem_edit"),
    path("ordens/<int:pk>/executar/", OrdemProducaoExecutarView.as_view(), name="ordem_executar"),
]
