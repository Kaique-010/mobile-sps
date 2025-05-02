# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ListaCasamentoViewSet, ItensListaCasamentoViewSet

router = DefaultRouter()
router.register(r'listas-casamento', ListaCasamentoViewSet,  basename='listacasamento')
router.register(r'itens', ItensListaCasamentoViewSet, basename='itenslistacasamento')

urlpatterns = router.urls