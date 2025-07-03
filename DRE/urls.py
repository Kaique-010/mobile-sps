from django.urls import path
from DRE.views import DREGerencialDinamicoView

urlpatterns = [
    path('dre_gerencial/', DREGerencialDinamicoView.as_view(), name='dre-gerencial'),
]
