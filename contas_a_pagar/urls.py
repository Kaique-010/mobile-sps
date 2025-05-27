from rest_framework.routers import DefaultRouter
from .views import TitulospagarViewSet

router = DefaultRouter()
router.register(r'titulos-pagar', TitulospagarViewSet)

urlpatterns = router.urls
