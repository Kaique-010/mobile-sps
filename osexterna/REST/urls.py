from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import OsexternaViewSet, ServicososexternaViewSet

router = DefaultRouter()
router.register(r'ordens', OsexternaViewSet, basename='osexterna-ordens')
router.register(r'servicos', ServicososexternaViewSet, basename='osexterna-servicos')

urlpatterns = []

# Rota de PATCH separada para não bloquear GET da lista
urlpatterns += [
    path('ordens/patch/', OsexternaViewSet.as_view({'patch': 'patch_ordem'}), name='osexterna-ordens-patch'),
]

urlpatterns += router.urls
