from rest_framework.routers import DefaultRouter
from .views import ImplantacaoTelaViewSet

router = DefaultRouter()
router.register(r'implantacoes', ImplantacaoTelaViewSet)

urlpatterns = router.urls
