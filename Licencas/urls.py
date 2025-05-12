from django.urls import path
from .views import (
    LoginView,
    EmpresaUsuarioView,
    FiliaisPorEmpresaView,
    licencas_mapa,
)

urlpatterns = [
    # Rota pública (sem slug)
    path('login', LoginView.as_view(), name='login'),
    path('mapa/', licencas_mapa, name='licencas-mapa'),

    # Rotas privadas (com slug no include do core)
    path('empresas/', EmpresaUsuarioView.as_view(), name='empresa-list'),
    path('filiais/', FiliaisPorEmpresaView.as_view(), name='filial-list'),
]
