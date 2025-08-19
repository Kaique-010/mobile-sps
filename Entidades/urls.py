from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import EntidadesViewSet, EntidadesLoginViewSet, EntidadesRefreshViewSet


router = DefaultRouter()
router.register(r'entidades', EntidadesViewSet, basename='entidades')

# Rota específica para login
urlpatterns = [
    path('login/', EntidadesLoginViewSet.as_view({'post': 'create'}), name='entidades-login'),
    path('refresh/', EntidadesRefreshViewSet.as_view({'post': 'create'}), name='entidades-refresh'),
] + router.urls