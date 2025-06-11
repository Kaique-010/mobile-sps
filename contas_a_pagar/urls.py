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

urlpatterns = [
    path('', include(router.urls)),
    path(
        'titulos-pagar/<int:titu_empr>/<int:titu_fili>/<int:titu_forn>/<str:titu_titu>/<str:titu_seri>/<str:titu_parc>/',
        titulos_detail,
        name='titulospagar-detail'
    ),
]
