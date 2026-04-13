from django.urls import path

from .views import ConfirmarImportacaoView, UploadImportadorView
from .views_entidades import ConfirmarImportacaoEntidadesView, UploadImportadorEntidadesView

urlpatterns = [
    path("", UploadImportadorView.as_view(), name="importar_produtos"),
    path("importar-produtos/confirmar/", ConfirmarImportacaoView.as_view(), name="confirmar_importacao_produtos"),
    path("entidades/", UploadImportadorEntidadesView.as_view(), name="importar_entidades"),
    path("entidades/confirmar/", ConfirmarImportacaoEntidadesView.as_view(), name="confirmar_importacao_entidades"),
]
