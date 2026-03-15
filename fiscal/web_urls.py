from django.urls import path

from fiscal.web_views import DevolucoesView

urlpatterns = [
    path("devolucoes/", DevolucoesView.as_view(), name="fiscal-devolucoes"),
]

