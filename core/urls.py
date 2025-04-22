from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('Auth.urls')),
    path('api/', include('Produtos.urls')),
    path('api/', include('Entidades.urls')),
    path('api/', include('Pedidos.urls')), 
    path('api/', include('dashboards.urls')),
    path('api/', include('listacasamento.urls')),
    
]
