from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .REST.views import CaixaViewSet
from .views import CaixageralViewSet, MovicaixaViewSet

router = DefaultRouter()
router.register(r'caixa', CaixaViewSet, basename='caixa')
router.register(r'caixageral', CaixageralViewSet, basename='caixageral')
router.register(r'movicaixa', MovicaixaViewSet, basename='movicaixa')

urlpatterns = router.urls