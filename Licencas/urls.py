from django.urls import path
from .views import LoginView, EmpresaUsuarioView, FiliaisPorEmpresaView, AlterarSenhaView
from rest_framework.routers import DefaultRouter
from .views import  UsuariosViewSet

router = DefaultRouter()
router.register(r'usuarios', UsuariosViewSet, basename='usuario')



urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('empresas/', EmpresaUsuarioView.as_view(), name='empresa-list'),
    path('filiais/', FiliaisPorEmpresaView.as_view(), name='filial-list'),
    path('alterar-senha/', AlterarSenhaView.as_view(), name='alterar-senha'),
    
]
urlpatterns += router.urls
