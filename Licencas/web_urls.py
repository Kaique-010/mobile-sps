from django.urls import path
from .web_views import (
    FilialCertificadoUploadView,
    EmpresaListView,
    EmpresaCreateView,
    EmpresaUpdateView,
    FilialListView,
    FilialCreateView,
    FilialUpdateView,
    UserListView,
    UserCreateView,
    UserEditView,
    UserDeleteView,
)

urlpatterns = [
    path('certificados/a1-upload/', FilialCertificadoUploadView.as_view(), name='web_licencas_certificado'),
    path('empresas/', EmpresaListView.as_view(), name='empresas_web'),
    path('empresas/new/', EmpresaCreateView.as_view(), name='empresa_create_web'),
    path('empresas/<int:empr_codi>/edit/', EmpresaUpdateView.as_view(), name='empresa_edit_web'),
    path('filiais/', FilialListView.as_view(), name='filiais_web'),
    path('filiais/new/', FilialCreateView.as_view(), name='filial_create_web'),
    path('filiais/<int:empr_empr>/edit/', FilialUpdateView.as_view(), name='filial_edit_web'),
    path('users/', UserListView.as_view(), name='users_list'),
    path('users/create/', UserCreateView.as_view(), name='users_create'),
    path('users/edit/<int:id>/', UserEditView.as_view(), name='users_edit'),
    path('users/delete/<int:id>/', UserDeleteView.as_view(), name='users_delete'),
]
