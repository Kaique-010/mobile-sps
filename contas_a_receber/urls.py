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

# Ações customizadas
baixar_titulo = TitulosreceberViewSet.as_view({
    'post': 'baixar_titulo'
})

historico_baixas = TitulosreceberViewSet.as_view({
    'get': 'historico_baixas'
})

urlpatterns = [
    path('', include(router.urls)),
    path(
        'titulos-receber/<int:titu_empr>/<int:titu_fili>/<int:titu_clie>/<str:titu_titu>/<str:titu_seri>/<str:titu_parc>/<str:titu_emis>/<str:titu_venc>/',
        titulos_detail,
        name='titulosreceber-detail'
    ),
    path(
        'titulos-receber/<int:titu_empr>/<int:titu_fili>/<int:titu_clie>/<str:titu_titu>/<str:titu_seri>/<str:titu_parc>/<str:titu_emis>/<str:titu_venc>/baixar/',
        baixar_titulo,
        name='titulosreceber-baixar'
    ),
    path(
        'titulos-receber/<int:titu_empr>/<int:titu_fili>/<int:titu_clie>/<str:titu_titu>/<str:titu_seri>/<str:titu_parc>/<str:titu_emis>/<str:titu_venc>/historico-baixas/',
        historico_baixas,
        name='titulosreceber-historico-baixas'
    ),
]
