from django.urls import path

from .Views import (
    OrdemproducaoListView,
    OrdemproducaoCreateView,
    OrdemproducaoUpdateView,
    OrdemproducaoDeleteView,
)

app_name = 'ordem_producao_web'

urlpatterns = [
    path('', OrdemproducaoListView.as_view(), name='ordemproducao_list'),
    path('nova/', OrdemproducaoCreateView.as_view(), name='ordemproducao_create'),
    path('<int:orpr_codi>/editar/', OrdemproducaoUpdateView.as_view(), name='ordemproducao_update'),
    path('<int:orpr_codi>/excluir/', OrdemproducaoDeleteView.as_view(), name='ordemproducao_delete'),
]
