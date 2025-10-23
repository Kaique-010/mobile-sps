# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PropriedadesViewSet, fluxo_gerencial

router = DefaultRouter()
router.register(r'propriedades', PropriedadesViewSet, basename='propriedades')

urlpatterns = router.urls + [
    path('fluxo-gerencial/', fluxo_gerencial, name='fluxo-gerencial'),
]
