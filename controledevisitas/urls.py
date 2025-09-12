from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ControleVisitaViewSet, EtapaVisitaViewSet, ItensVisitaViewSet

router = DefaultRouter()

router.register(r'controle-visitas', ControleVisitaViewSet, basename='controle-visitas')
router.register(r'etapas-visita', EtapaVisitaViewSet, basename='etapas-visita')
router.register(r'itens-visita', ItensVisitaViewSet, basename='itens-visita')

urlpatterns = [
    path('', include(router.urls)),
]
