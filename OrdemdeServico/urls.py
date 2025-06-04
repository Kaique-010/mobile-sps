from rest_framework import routers
from .views import *

router = routers.DefaultRouter()
router.register(r'ordens', OrdemServicoViewSet, basename='ordens')
router.register(r'pecas', OrdemServicoPecasViewSet, basename='pecas')
router.register(r'servicos', OrdemServicoServicosViewSet, basename='servicos')
router.register(r'fotos', FotosViewSet, basename='fotos')
router.register(r'imagens/antes', ImagemAntesViewSet, 'imagensantes')
router.register(r'imagens/durante', ImagemDuranteViewSet, 'iamegsndurante')
router.register(r'imagens/depois', ImagemDepoisViewSet, basename='imagensdepois')

urlpatterns = router.urls
