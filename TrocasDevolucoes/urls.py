from rest_framework.routers import DefaultRouter

from TrocasDevolucoes.rest.views import TrocaDevolucaoViewSet

router = DefaultRouter()
router.register(r'devolucoes', TrocaDevolucaoViewSet, basename='trocas-devolucoes')

urlpatterns = router.urls
