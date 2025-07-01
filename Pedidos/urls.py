# urls.py
from email.mime import base
from rest_framework.routers import DefaultRouter
from .views import PedidoVendaViewSet
from .views_dashboard import PedidosGeralViewSet

router = DefaultRouter()
router.register(r'pedidos', PedidoVendaViewSet, basename='pedidos')
router.register(r'pedidos-geral', PedidosGeralViewSet, basename='pedidos-geral')

urlpatterns = router.urls
