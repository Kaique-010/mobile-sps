from django.urls import path
from .views.titulo_api import GerarBoletoAPIView
from .views.titulo_api import ConsultarBoletoAPIView, CancelarBoletoAPIView
from .views.sicredi_api import SicrediTokenAPIView, SicrediBoletoAPIView

urlpatterns = [
    path("titulo/<int:pk>/gerar/", GerarBoletoAPIView.as_view()),
    path("titulo/<int:pk>/consultar/", ConsultarBoletoAPIView.as_view()),
    path("titulo/<int:pk>/cancelar/", CancelarBoletoAPIView.as_view()),
    path("sicredi/carteira/<int:carteira_codigo>/token/", SicrediTokenAPIView.as_view()),
    path("sicredi/carteira/<int:carteira_codigo>/boletos/", SicrediBoletoAPIView.as_view()),
]
