from django.urls import path
from .Views.listar import CFOPListView
from .Views.criar import CFOPCreateView
from .Views.editar import CFOPUpdateView
from .Views.import_export import CFOPExportView
from .Views.autocomplete import cfop_autocomplete, cfop_exigencias_ajax



urlpatterns = [
    path('', CFOPListView.as_view(), name='cfop_list_web'),
    path('new/', CFOPCreateView.as_view(), name='cfop_create_web'),
    path('<int:empr>/<int:codi>/edit/', CFOPUpdateView.as_view(), name='cfop_edit_web'),
    path('export/', CFOPExportView.as_view(), name='cfop_export_web'),
    path('autocomplete/', cfop_autocomplete, name='cfop_autocomplete'),
    path('exigencias/', cfop_exigencias_ajax, name='cfop_exigencias_ajax'),

]