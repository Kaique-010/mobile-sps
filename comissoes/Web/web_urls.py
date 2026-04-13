from django.urls import path
from .Views.autocompletes import autocomplete_entidades, autocomplete_centrosdecustos
from .Views import painel, regras, lancamentos, pagamentos

app_name = "comissoes_web"

urlpatterns = [
    path("", painel.painel_view, name="painel"),
    path("autocompletes/entidades/", autocomplete_entidades, name="autocomplete_entidades"),
    path("autocompletes/centrosdecustos/", autocomplete_centrosdecustos, name="autocomplete_centrosdecustos"),
    path("regras/", regras.lista, name="regras_list"),
    path("regras/criar/", regras.criar, name="regras_create"),
    path("regras/<int:regra_id>/editar/", regras.editar, name="regras_edit"),
    path("lancamentos/", lancamentos.lista, name="lancamentos_list"),
    path("pagamentos/", pagamentos.lista, name="pagamentos_list"),
    path("pagamentos/criar/", pagamentos.criar, name="pagamentos_create"),
    path("pagamentos/<int:pagamento_id>/", pagamentos.detalhe, name="pagamentos_detail"),
]
