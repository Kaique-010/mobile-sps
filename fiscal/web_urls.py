from django.urls import path

from fiscal.web_views import DevolucoesView, EntradasXMLView

urlpatterns = [
    path("devolucoes/", DevolucoesView.as_view(), name="fiscal-devolucoes"),
    path("entradas-xml/", EntradasXMLView.as_view(), name="fiscal-entradas-xml"),
]

