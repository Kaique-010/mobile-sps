# processos/web/urls.py

from django.urls import path
from .web.views.list import ProcessoListView
from .web.views.create import ProcessoCreateView
from .web.views.delete import ProcessoDeleteView
from .web.views.detail import ProcessoDetailView
from .web.views.savechecklist import SalvarChecklistView
from .web.views.savechecklist import ValidarProcessoView



app_name = "processos"

urlpatterns = [
    path("", ProcessoListView.as_view(), name="lista"),
    path("create/", ProcessoCreateView.as_view(), name="criar"),
    path("<int:pk>/delete/", ProcessoDeleteView.as_view(), name="excluir"),
    path("<int:pk>/", ProcessoDetailView.as_view(), name="detalhe"),
    path("<int:pk>/checklist/salvar/", SalvarChecklistView.as_view(), name="salvar_checklist"),
    path("<int:pk>/validar/", ValidarProcessoView.as_view(), name="validar"),
]