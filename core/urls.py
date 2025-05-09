from django.contrib import admin
from rest_framework_simplejwt.views import (
   
    TokenRefreshView,
)
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/licencas/', include('Licencas.urls')),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include('Produtos.urls')),
    path('api/', include('Entidades.urls')),
    path('api/', include('Pedidos.urls')), 
    path('api/', include('dashboards.urls')),
    path('api/', include('Entradas_Estoque.urls')),
    path('api/', include('listacasamento.urls')),
    path('api/', include('Saidas_Estoque.urls')),
    
]
