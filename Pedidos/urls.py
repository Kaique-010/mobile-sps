# urls.py
from rest_framework.routers import DefaultRouter
from .views import PedidoVendaViewSet

router = DefaultRouter()
router.register(r'pedidos', PedidoVendaViewSet)

urlpatterns = router.urls
