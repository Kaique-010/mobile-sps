from django.urls import path
from .web_views import (
    EntidadeListView,
    EntidadeCreateView,
    EntidadeUpdateView,
    EntidadeDeleteView,
    ExportarEntidadesView,
)

urlpatterns = [
    path('', EntidadeListView.as_view(), name='entidades_web'),
    path('novo/', EntidadeCreateView.as_view(), name='entidade_form_web'),
    path('<int:enti_clie>/editar/', EntidadeUpdateView.as_view(), name='entidade_update_web'),
    path('<int:enti_clie>/excluir/', EntidadeDeleteView.as_view(), name='entidade_delete_web'),
    path('exportar/', ExportarEntidadesView.as_view(), name='exportar_entidades_web'),
]