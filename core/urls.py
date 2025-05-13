# core/urls.py
from django.contrib import admin
from rest_framework_simplejwt.views import TokenRefreshView
from django.urls import path, include
from Licencas.views import LoginView, licencas_mapa  # Importando a view do mapa

from django.contrib import admin
from django.urls import path, include
from Licencas.views import licencas_mapa

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Rota pública (sem slug)
    path('api/licencas/mapa/', licencas_mapa, name='licencas-mapa'),

    # Rotas privadas (com slug automático)
    path('api/<slug>/licencas/', include('Licencas.urls')),
    path('api/<slug>/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('api/<slug>/produtos/', include('Produtos.urls')),
    path('api/<slug>/entidades/', include('Entidades.urls')),
    path('api/<slug>/pedidos/', include('Pedidos.urls')),
    path('api/<slug:slug>/dashboards/', include('dashboards.urls')),
    path('api/<slug>/entradas_estoque/', include('Entradas_Estoque.urls')),
    path('api/<slug>/listacasamento/', include('listacasamento.urls')),
    path('api/<slug>/saidas_estoque/', include('Saidas_Estoque.urls')),
]
