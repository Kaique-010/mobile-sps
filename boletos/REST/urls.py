from django.urls import path
from .views.titulo_api import GerarBoletoAPIView
from .views.titulo_api import ConsultarBoletoAPIView, CancelarBoletoAPIView
from .views.sicredi_online_api import SicrediTokenAPIView, SicrediBoletoAPIView
from .views.bradesco_online_api import BradescoTokenAPIView, BradescoBoletoAPIView
from .views.itau_online_api import ItauTokenAPIView, ItauBoletoAPIView
from .views.cora_online_api import CoraTokenAPIView, CoraBoletoAPIView
from .views.bb_online_api import BancoBrasilTokenAPIView, BancoBrasilBoletoAPIView

urlpatterns = [
    path("titulo/<int:pk>/gerar/", GerarBoletoAPIView.as_view()),
    path("titulo/<int:pk>/consultar/", ConsultarBoletoAPIView.as_view()),
    path("titulo/<int:pk>/cancelar/", CancelarBoletoAPIView.as_view()),
    path("sicredi/carteira/<int:carteira_codigo>/token/", SicrediTokenAPIView.as_view()),
    path("sicredi/carteira/<int:carteira_codigo>/boletos/", SicrediBoletoAPIView.as_view()),
    path("bradesco/carteira/<int:carteira_codigo>/token/", BradescoTokenAPIView.as_view()),
    path("bradesco/carteira/<int:carteira_codigo>/boletos/", BradescoBoletoAPIView.as_view()),
    path("itau/carteira/<int:carteira_codigo>/token/", ItauTokenAPIView.as_view()),
    path("itau/carteira/<int:carteira_codigo>/boletos/", ItauBoletoAPIView.as_view()),
    path("cora/carteira/<int:carteira_codigo>/token/", CoraTokenAPIView.as_view()),
    path("cora/carteira/<int:carteira_codigo>/boletos/", CoraBoletoAPIView.as_view()),
    path("bb/carteira/<int:carteira_codigo>/token/", BancoBrasilTokenAPIView.as_view()),
    path("bb/carteira/<int:carteira_codigo>/boletos/", BancoBrasilBoletoAPIView.as_view()),
]
