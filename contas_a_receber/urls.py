from rest_framework.routers import DefaultRouter
from .views import TitulosreceberViewSet

router = DefaultRouter()

router.register(r'titulos-receber', TitulosreceberViewSet)

urlpatterns = router.urls
