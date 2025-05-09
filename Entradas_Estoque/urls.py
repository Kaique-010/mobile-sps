# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EntradasEstoqueViewSet

router = DefaultRouter()
router.register(r'entradas-estoque', EntradasEstoqueViewSet, basename='entradas-estoque')

urlpatterns = router.urls
