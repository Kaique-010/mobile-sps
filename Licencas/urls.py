from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LoginView,
    EmpresaUsuarioView,
    FiliaisPorEmpresaView,
    
)
from rest_framework_simplejwt.views import TokenRefreshView 

router = DefaultRouter()

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('empresas/', EmpresaUsuarioView.as_view(), name='empresa-list'),
    path('filiais/', FiliaisPorEmpresaView.as_view(), name='filial_list'),    
    
]
