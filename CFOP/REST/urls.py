from django.urls import path
from rest_framework.routers import DefaultRouter
from .viewsets import CFOPBuscaViewSet

router = DefaultRouter()
router.register(r"busca", CFOPBuscaViewSet, basename="cfop-busca")

urlpatterns = router.urls + [

]