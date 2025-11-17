from rest_framework.routers import DefaultRouter
from .views import SaidasEstoqueViewSet

router = DefaultRouter()
router.register(r"saidas-estoque", SaidasEstoqueViewSet, basename="saidas-estoque")

urlpatterns = router.urls