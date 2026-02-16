from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import AdiantamentosViewSet


router = DefaultRouter()
router.register(r'', AdiantamentosViewSet, basename='adiantamentos')


urlpatterns = [
    path('', include(router.urls)),
]

