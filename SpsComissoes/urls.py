# urls.py

from rest_framework.routers import DefaultRouter
from .views import ComissaoSpsViewSet

router = DefaultRouter()
router.register(r'comissoes-sps', ComissaoSpsViewSet)

urlpatterns = router.urls
