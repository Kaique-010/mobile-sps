from rest_framework.routers import DefaultRouter
from .views import ContratosViewSet

router = DefaultRouter()

router.register(r'contratos-vendas', ContratosViewSet, basename='contratos')

urlpatterns = router.urls
