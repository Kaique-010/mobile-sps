from django.urls import path, include
from rest_framework.routers import DefaultRouter
from transportes.views import api
from transportes.Rest.Views.abastecimentos import AbastecimentoViewSet
from transportes.Rest.Views.bombas_saldos import BombasSaldosViewSet

router = DefaultRouter()
router.register(r'ctes', api.CteViewSet, basename='api-cte')
router.register(r'mdfes', api.MdfeViewSet, basename='api-mdfe')
router.register(r'abastecimentos', AbastecimentoViewSet, basename='api-abastecimento')
router.register(r'bombas_saldos', BombasSaldosViewSet, basename='api-bombas-saldos')

urlpatterns = [
    path('', include(router.urls)),
]
