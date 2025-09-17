# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LctobancarioViewSet

router = DefaultRouter()
router.register(r'lctobancarios', LctobancarioViewSet, basename='lctobancarios')

urlpatterns = [
    path('', include(router.urls)),
]
