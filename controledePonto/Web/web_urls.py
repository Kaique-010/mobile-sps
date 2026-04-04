from django.urls import path

from controledePonto.Web.Views.createView import RegistroPontoCreateView
from controledePonto.Web.Views.listView import RegistroPontoListView

app_name = 'controledePonto_web'

urlpatterns = [
    path('', RegistroPontoListView.as_view(), name='registro_ponto_list'),
    path('registrar/', RegistroPontoCreateView.as_view(), name='registro_ponto_registrar'),
]
