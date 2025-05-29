
from rest_framework.routers import DefaultRouter
from .views import CaixageralViewSet, MovicaixaViewSet

router = DefaultRouter()
router.register(r'caixageral', CaixageralViewSet, basename='caixageral')
router.register(r'movicaixa', MovicaixaViewSet, basename='movicaixa')

urlpatterns = router.urls