from rest_framework.routers import DefaultRouter
from django.urls import path, include
from coletaestoque.views import ColetaEstoqueViewSet

router = DefaultRouter()
router.register(r'', ColetaEstoqueViewSet, basename='coletaestoque')

urlpatterns = [
    path('', include(router.urls)),
]