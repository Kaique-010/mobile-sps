# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PropriedadesViewSet

router = DefaultRouter()
router.register(r'propriedades', PropriedadesViewSet, basename='propriedades')

urlpatterns = router.urls
