# central/urls.py
from django.urls import path
from .views import (
    CentralListView,
    CentralDetailView,
    CentralCreateView,
    CentralUpdateView,
)

urlpatterns = [
    path("", CentralListView.as_view(), name="central_lista"),
    path("<int:pk>/", CentralDetailView.as_view(), name="central_detalhe"),
    path("novo/", CentralCreateView.as_view(), name="central_criar"),
    path("<int:pk>/editar/", CentralUpdateView.as_view(), name="central_editar"),
]
