from django.urls import path
from rest_framework.routers import DefaultRouter
from .viewsets import CfopBuscaViewSet
from CFOP.REST.views_extras import sugerir_tributacao, cfop_autocomplete

router = DefaultRouter()
router.register(r"busca", CfopBuscaViewSet, basename="cfop-busca")

urlpatterns = router.urls + [
    path('sugerir-tributacao/', sugerir_tributacao, name='cfop_sugerir_tributacao'),
    path('autocomplete/', cfop_autocomplete, name='cfop_autocomplete'),
]