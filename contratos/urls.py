from rest_framework.routers import DefaultRouter
from .Rest.views import ContratoViewSet

router = DefaultRouter()

router.register(r'contratos-vendas', ContratoViewSet, basename='contratos')

urlpatterns = router.urls
