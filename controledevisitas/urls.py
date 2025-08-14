from rest_framework.routers import DefaultRouter
from .views import ControleVisitaViewSet, EtapaVisitaViewSet

router = DefaultRouter()

router.register(r'controle-visitas', ControleVisitaViewSet, basename='controle-visitas')
router.register(r'etapas-visita', EtapaVisitaViewSet, basename='etapas-visita')

urlpatterns = router.urls
