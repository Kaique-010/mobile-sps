from django.urls import path
from .views import (
    LoginView,
    EmpresaUsuarioView,
    FiliaisPorEmpresaView,
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('empresas/', EmpresaUsuarioView.as_view(), name='empresa-list'),
    path('filiais/', FiliaisPorEmpresaView.as_view(), name='filial_list'),
]
