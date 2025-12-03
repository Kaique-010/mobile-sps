from django.urls import path
from .Views.list import ColetaListView, ColetaResumoView
from .Views.registrar import ColetaRegistrarView

app_name = 'ColetaEstoqueWeb'

urlpatterns = [
    path('', ColetaListView.as_view(), name='coleta_list_web'),
    path('resumo/', ColetaResumoView.as_view(), name='coleta_resumo_web'),
    path('novo/', ColetaRegistrarView.as_view(), name='coleta_registrar_web'),
]
