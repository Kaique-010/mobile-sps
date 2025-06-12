from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LogAcaoViewSet

router = DefaultRouter()
router.register('logs', LogAcaoViewSet, basename='logs')

urlpatterns = [
    path('', include(router.urls)),
    # O endpoint admin será acessível em /api/auditoria/logs/admin/
    path('logs/admin/', LogAcaoViewSet.as_view({'get': 'admin'}), name='logs-admin'),
]