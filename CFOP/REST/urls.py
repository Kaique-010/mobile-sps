from django.urls import path
from rest_framework.routers import DefaultRouter
from .viewsets import CFOPViewSet

router = DefaultRouter()
router.register(r"cfop", CFOPViewSet, basename="cfop")
router.register(r"cfop", CFOPViewSet, basename="cfop-legacy")

urlpatterns = router.urls + [

]
