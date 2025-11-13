from django.urls import path
from .web_views import FilialCertificadoUploadView, EmpresaListView, EmpresaCreateView, EmpresaUpdateView, FilialListView, FilialCreateView, FilialUpdateView

urlpatterns = [
    path('certificados/a1-upload/', FilialCertificadoUploadView.as_view(), name='web_licencas_certificado'),
    path('empresas/', EmpresaListView.as_view(), name='empresas_web'),
    path('empresas/new/', EmpresaCreateView.as_view(), name='empresa_create_web'),
    path('empresas/<int:empr_codi>/edit/', EmpresaUpdateView.as_view(), name='empresa_edit_web'),
    path('filiais/', FilialListView.as_view(), name='filiais_web'),
    path('filiais/new/', FilialCreateView.as_view(), name='filial_create_web'),
    path('filiais/<int:empr_empr>/edit/', FilialUpdateView.as_view(), name='filial_edit_web'),
]
