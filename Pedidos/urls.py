# urls.py
from email.mime import base
from rest_framework.routers import DefaultRouter
from .views import PedidoVendaViewSet

router = DefaultRouter()
router.register(r'pedidos', PedidoVendaViewSet, basename='pedidos')

urlpatterns = router.urls
