from rest_framework.routers import DefaultRouter
from .views import EnviarCobrancaViewSet

router = DefaultRouter()
router.register(r'enviar-cobranca', EnviarCobrancaViewSet, basename='enviar-cobranca')
urlpatterns = router.urls
