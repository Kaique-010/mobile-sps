from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TitulospagarViewSet

router = DefaultRouter()
router.register(r'titulos-pagar', TitulospagarViewSet, basename='titulospagar')

titulos_detail = TitulospagarViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy',
})

# Ações customizadas
baixar_titulo = TitulospagarViewSet.as_view({
    'post': 'baixar_titulo'
})

historico_baixas = TitulospagarViewSet.as_view({
    'get': 'historico_baixas'
})

urlpatterns = [
    path('', include(router.urls)),
    path(
        'titulos-pagar/<int:titu_empr>/<int:titu_fili>/<int:titu_forn>/<str:titu_titu>/<str:titu_seri>/<str:titu_parc>/<str:titu_emis>/<str:titu_venc>/',
        titulos_detail,
        name='titulospagar-detail'
    ),
    path(
        'titulos-pagar/<int:titu_empr>/<int:titu_fili>/<int:titu_forn>/<str:titu_titu>/<str:titu_seri>/<str:titu_parc>/<str:titu_emis>/<str:titu_venc>/baixar/',
        baixar_titulo,
        name='titulospagar-baixar'
    ),
    path(
        'titulos-pagar/<int:titu_empr>/<int:titu_fili>/<int:titu_forn>/<str:titu_titu>/<str:titu_seri>/<str:titu_parc>/<str:titu_emis>/<str:titu_venc>/historico_baixas/',
        historico_baixas,
        name='titulospagar-historico-baixas'
    ),
]
