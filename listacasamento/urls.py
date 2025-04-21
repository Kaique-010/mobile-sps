# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ListaCasamentoViewSet

router = DefaultRouter()
router.register(r'listas-casamento', ListaCasamentoViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
