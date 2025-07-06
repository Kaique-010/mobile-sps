from django.urls import path
from DRE.views import DREGerencialDinamicoView, DRECaixaView

urlpatterns = [
    path('dre_gerencial/', DREGerencialDinamicoView.as_view(), name='dre-gerencial'),
    path('dre-caixa/', DRECaixaView.as_view(), name='dre-caixa'),
]
