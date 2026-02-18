from django.urls import path
from .web_views import RenegociacaoListView, RenegociacaoCreateView, RenegociacaoEditView

urlpatterns = [
    path("renegociacoes/", RenegociacaoListView.as_view(), name="renegociacao_list"),
    path("renegociacoes/nova/", RenegociacaoCreateView.as_view(), name="renegociacao_create"),
    path("renegociacoes/<int:rene_id>/editar/", RenegociacaoEditView.as_view(), name="renegociacao_edit"),
]
