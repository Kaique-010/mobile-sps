from django.urls import path

from fiscal.api.views import (
    DocumentoDetailView,
    DocumentosView,
    GerarDevolucaoView,
    GerarEntradaView,
    ImportarXMLView,
    WizardEntradasListView,
    WizardAutoMapearView,
    WizardCriarProdutosView,
    WizardFinalizarView,
    WizardFinanceiroView,
    WizardIniciarView,
    WizardPreprocessarView,
)


urlpatterns = [
    path("nfe/importar/", ImportarXMLView.as_view(), name="fiscal-nfe-importar"),
    path("nfe/documentos/", DocumentosView.as_view(), name="fiscal-nfe-documentos"),
    path("nfe/documentos/<int:documento_id>/", DocumentoDetailView.as_view(), name="fiscal-nfe-documento-detail"),
    path("nfe/devolucao/", GerarDevolucaoView.as_view(), name="fiscal-nfe-devolucao"),
    path("nfe/entrada/", GerarEntradaView.as_view(), name="fiscal-nfe-entrada"),
    path("nfe/wizard/iniciar/", WizardIniciarView.as_view(), name="fiscal-nfe-wizard-iniciar"),
    path("nfe/wizard/entradas/", WizardEntradasListView.as_view(), name="fiscal-nfe-wizard-entradas"),
    path("nfe/wizard/<int:nota_id>/preprocessar/", WizardPreprocessarView.as_view(), name="fiscal-nfe-wizard-preprocessar"),
    path("nfe/wizard/<int:nota_id>/auto-mapear/", WizardAutoMapearView.as_view(), name="fiscal-nfe-wizard-auto-mapear"),
    path("nfe/wizard/<int:nota_id>/criar-produtos/", WizardCriarProdutosView.as_view(), name="fiscal-nfe-wizard-criar-produtos"),
    path("nfe/wizard/<int:nota_id>/financeiro/", WizardFinanceiroView.as_view(), name="fiscal-nfe-wizard-financeiro"),
    path("nfe/wizard/<int:nota_id>/finalizar/", WizardFinalizarView.as_view(), name="fiscal-nfe-wizard-finalizar"),
]

