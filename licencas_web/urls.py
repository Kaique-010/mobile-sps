from django.urls import path
from .views import licencas_web_mapa


urlpatterns = [
    path('mapa/', licencas_web_mapa, name='licencas-web-mapa'),
]

