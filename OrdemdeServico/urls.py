from rest_framework import routers
from .views import *

router = routers.DefaultRouter()
router.register(r'ordens', OrdemServicoViewSet)
router.register(r'pecas', OrdemServicoPecasViewSet)
router.register(r'servicos', OrdemServicoServicosViewSet)
router.register(r'imagens/antes', ImagemAntesViewSet)
router.register(r'imagens/durante', ImagemDuranteViewSet)
router.register(r'imagens/depois', ImagemDepoisViewSet)

urlpatterns = router.urls
