# processos/web/urls.py

from django.urls import path
from .web.views import list
from .web.views.create import ProcessoCreateView
from .web.views.delete import ProcessoDeleteView
from .web.views.detail import ProcessoDetailView
from .web.views.savechecklist import SalvarChecklistView
from .web.views.savechecklist import ValidarProcessoView



app_name = "processos"

urlpatterns = [
    path("", list, name="lista"),
    path("create/", ProcessoCreateView, name="criar"),
    path("<int:pk>/delete/", ProcessoDeleteView, name="excluir"),
    path("<int:pk>/", ProcessoDetailView, name="detalhe"),
    path("<int:pk>/checklist/salvar/", SalvarChecklistView.as_view(), name="salvar_checklist"),
    path("<int:pk>/validar/", ValidarProcessoView.as_view(), name="validar"),
]