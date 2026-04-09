from django.urls import path

from TrocasDevolucoes.Web.Views.createView import DevolucaoCreateView
from TrocasDevolucoes.Web.Views.listView import DevolucoesListView
from TrocasDevolucoes.Web.Views.updateView import DevolucaoUpdateView

app_name = 'TrocasDevolucoesWeb'

urlpatterns = [
    path('', DevolucoesListView.as_view(), name='devolucoes_listar'),
    path('criar/', DevolucaoCreateView.as_view(), name='devolucao_criar'),
    path('<int:pk>/editar/', DevolucaoUpdateView.as_view(), name='devolucao_editar'),
]
