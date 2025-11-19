from django.urls import path
from .Web.Views.nota.nota_list import NotaListView
from .Web.Views.nota.nota_create import NotaCreateView
from .Web.Views.nota.nota_detail import NotaDetailView
from .Web.Views.nota.nota_update import NotaUpdateView

app_name = "NotasFiscaisWeb"

urlpatterns = [
    path("", NotaListView.as_view(), name="nota_list"),
    path("novo/", NotaCreateView.as_view(), name="nota_create"),
    path("<int:pk>/", NotaDetailView.as_view(), name="nota_detail"),
    path("<int:pk>/editar/", NotaUpdateView.as_view(), name="nota_update"),
]