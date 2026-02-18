from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .rest.views import RenegociadoViewSet

router = DefaultRouter()
router.register(r"renegociacoes", RenegociadoViewSet, basename="renegociado")

urlpatterns = [
    path("", include(router.urls)),
]

