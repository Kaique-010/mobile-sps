from django.urls import path

from Gerencial.Views.financeiro import DespesasPrevistasView, FluxoCaixaPrevistoView, LucroPrevistoView


urlpatterns = [
    path('financeiro/despesas-previstas/', DespesasPrevistasView.as_view()),
    path('financeiro/fluxo-previsto/', FluxoCaixaPrevistoView.as_view()),
    path('financeiro/lucro-previsto/', LucroPrevistoView.as_view()),

]
