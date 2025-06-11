from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TitulosreceberViewSet

router = DefaultRouter()
router.register(r'titulos-receber', TitulosreceberViewSet, basename='titulosreceber')

titulos_detail = TitulosreceberViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy',
})

urlpatterns = [
    path('', include(router.urls)),
    path(
        'titulos-receber/<int:titu_empr>/<int:titu_fili>/<int:titu_clie>/<str:titu_titu>/<str:titu_seri>/<str:titu_parc>/',
        titulos_detail,
        name='titulosreceber-detail'
    ),
]
