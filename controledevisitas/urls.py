from rest_framework.routers import DefaultRouter
from .views import ControleVisitaViewSet

router = DefaultRouter()

router.register(r'controle-visitas', ControleVisitaViewSet, basename='controle-visitas')

urlpatterns = router.urls
