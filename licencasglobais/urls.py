from rest_framework.routers import DefaultRouter
from .views import LicencaGlobalViewSet

router = DefaultRouter()
router.register(r'licencas-globais', LicencaGlobalViewSet)

urlpatterns = router.urls
