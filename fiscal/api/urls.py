from django.urls import path

from fiscal.api.views import DocumentoDetailView, DocumentosView, GerarDevolucaoView, ImportarXMLView


urlpatterns = [
    path("nfe/importar/", ImportarXMLView.as_view(), name="fiscal-nfe-importar"),
    path("nfe/documentos/", DocumentosView.as_view(), name="fiscal-nfe-documentos"),
    path("nfe/documentos/<int:documento_id>/", DocumentoDetailView.as_view(), name="fiscal-nfe-documento-detail"),
    path("nfe/devolucao/", GerarDevolucaoView.as_view(), name="fiscal-nfe-devolucao"),
]

