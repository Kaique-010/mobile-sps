from django.urls import path
from .views import UploadImportadorView, ConfirmarImportacaoView

urlpatterns = [
    path("", UploadImportadorView.as_view(), name="importar_produtos"),
    path("importar-produtos/confirmar/", ConfirmarImportacaoView.as_view(), name="confirmar_importacao_produtos"),
]
