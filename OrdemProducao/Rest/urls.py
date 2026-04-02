from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .Views import (
    OrdemproducaoViewSet,
    OrdemprodfotosViewSet,
    OrdemproditensViewSet,
    OrdemprodmateViewSet,
    OrdemprodetapaViewSet,
)

router = DefaultRouter()
router.register(r'ordens', OrdemproducaoViewSet, basename='ordemproducao')
router.register(r'fotos', OrdemprodfotosViewSet, basename='ordemprodfotos')
router.register(r'itens', OrdemproditensViewSet, basename='ordemproditens')
router.register(r'materiais', OrdemprodmateViewSet, basename='ordemprodmate')
router.register(r'etapas', OrdemprodetapaViewSet, basename='ordemprodetapa')

urlpatterns = [
    path('', include(router.urls)),
]
