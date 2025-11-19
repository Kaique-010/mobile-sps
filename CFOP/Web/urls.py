from django.urls import path
from .Views.listar import CfopListView
from .Views.criar import CfopCreateView
from .Views.editar import CfopUpdateView
from .Views.wizard import CfopWizardView
from .ajax import validate_unique_code
from .Views.import_export import CfopExportView, CfopImportView

urlpatterns = [
    path('', CfopListView.as_view(), name='cfop_list_web'),
    path('new/', CfopCreateView.as_view(), name='cfop_create_web'),
    path('<int:empr>/<int:codi>/edit/', CfopUpdateView.as_view(), name='cfop_edit_web'),
    path('wizard/', CfopWizardView.as_view(), name='cfop_wizard_web'),
    path('validate-unique/', validate_unique_code, name='cfop_validate_unique'),
    path('export/', CfopExportView.as_view(), name='cfop_export_web'),
    path('import/', CfopImportView.as_view(), name='cfop_import_web'),
]