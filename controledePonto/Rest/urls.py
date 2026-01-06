from rest_framework.routers import DefaultRouter
from .views import RegistroPontoViewSet


router = DefaultRouter()
router.register(r'pontos', RegistroPontoViewSet, basename='pontos')

urlpatterns = router.urls
