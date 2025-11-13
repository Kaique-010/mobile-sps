from django.urls import path
from .views import LoginView, EmpresaUsuarioView, FiliaisPorEmpresaView, AlterarSenhaView, UploadCertificadoA1View
from rest_framework.routers import DefaultRouter
from .views import  UsuariosViewSet, EmpresasViewSet, FiliaisViewSet

router = DefaultRouter()
router.register(r'usuarios', UsuariosViewSet, basename='usuario')
router.register(r'empresas', EmpresasViewSet, basename='empresas')
router.register(r'filiais-crud', FiliaisViewSet, basename='filiais-crud')



urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('empresas/', EmpresaUsuarioView.as_view(), name='empresa-list'),
    path('filiais/', FiliaisPorEmpresaView.as_view(), name='filial-list'),
    path('alterar-senha/', AlterarSenhaView.as_view(), name='alterar-senha'),
    path('filiais/upload-certificado/', UploadCertificadoA1View.as_view(), name='upload-certificado-a1'),
    
]
urlpatterns += router.urls
