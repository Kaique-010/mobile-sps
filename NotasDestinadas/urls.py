from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import NotasDestinadasViewSet, ImportarNotasDestinadasView

router = DefaultRouter()
router.register(r'destinadas', NotasDestinadasViewSet, basename='notas-destinadas')

urlpatterns = [
    path(
        'destinadas/<int:empresa>/<int:filial>/<int:numero>/processar/',
        NotasDestinadasViewSet.as_view({'post': 'processar'}),
        name='nota-destinada-processar'
    ),
    path(
        'destinadas/<int:empresa>/<int:filial>/<int:numero>/itens/',
        NotasDestinadasViewSet.as_view({'get': 'itens'}),
        name='nota-destinada-itens'
    ),
    path(
        'destinadas/<int:empresa>/<int:filial>/<int:numero>/preprocessar/',
        NotasDestinadasViewSet.as_view({'get': 'preprocessar'}),
        name='nota-destinada-preprocessar'
    ),
    path(
        'destinadas/<int:empresa>/<int:filial>/<int:numero>/confirmar/',
        NotasDestinadasViewSet.as_view({'post': 'confirmar'}),
        name='nota-destinada-confirmar'
    ),
    path(
        'destinadas/<int:empresa>/<int:filial>/<int:numero>/manifestar/',
        NotasDestinadasViewSet.as_view({'post': 'manifestar'}),
        name='nota-destinada-manifestar'
    ),
    path(
        'destinadas/<int:empresa>/<int:filial>/<int:numero>/criar-produto/',
        NotasDestinadasViewSet.as_view({'post': 'criar_produto'}),
        name='nota-destinada-criar-produto'
    ),
    path(
        'importar-notas-destinadas/',
        ImportarNotasDestinadasView.as_view(),
        name='importar-notas-destinadas'
    ),
    path(
        'produtos/buscar/',
        NotasDestinadasViewSet.as_view({'get': 'buscar_produtos'}),
        name='notas-destinadas-buscar-produtos'
    ),
    path(
        'config/',
        NotasDestinadasViewSet.as_view({'get': 'config'}),
        name='notas-destinadas-config'
    ),
]

urlpatterns += router.urls
