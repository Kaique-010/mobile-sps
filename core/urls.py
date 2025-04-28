from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/licencas/', include('Licencas.urls')),
    path('api/', include('Produtos.urls')),
    path('api/', include('Entidades.urls')),
    path('api/', include('Pedidos.urls')), 
    path('api/', include('dashboards.urls')),
    path('api/', include('listacasamento.urls')),
    
]
