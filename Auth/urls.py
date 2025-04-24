from django.urls import path
from .views import (
    LoginView,
    EmpresaUsuarioView,
    FiliaisPorEmpresaView,
    SetEmpresaFilialView
)
from rest_framework_simplejwt.views import TokenRefreshView  

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('empresas/', EmpresaUsuarioView.as_view(), name='empresa-list'),
    path('filiais/', FiliaisPorEmpresaView.as_view(), name='filial_list'),    
    path('set-empresa-filial/', SetEmpresaFilialView.as_view(), name='set-empresa-filial'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
