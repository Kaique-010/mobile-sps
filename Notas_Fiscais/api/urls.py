from django.urls import path
from . import emitir_view

urlpatterns = [
    path("emitir/<slug:slug>/<int:nota_id>/", emitir_view.emitir_nota),
]
