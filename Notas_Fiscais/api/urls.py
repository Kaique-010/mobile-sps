from django.urls import path
from . import emitir_view
from . import calculo_view

urlpatterns = [
    path("emitir/<slug:slug>/<int:nota_id>/", emitir_view.emitir_nota),
    path("imprimir/<slug:slug>/<int:nota_id>/", emitir_view.imprimir_danfe),
    path("calcular/<slug:slug>/<int:nota_id>/", calculo_view.calcular_impostos),
]
