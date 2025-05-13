from django.urls import path
from .views import LoginView, EmpresaUsuarioView, FiliaisPorEmpresaView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),  # <- precisa da barra!
    path('empresas/', EmpresaUsuarioView.as_view(), name='empresa-list'),
    path('filiais/', FiliaisPorEmpresaView.as_view(), name='filial-list'),
]
