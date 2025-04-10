# produtos/urls.py
from rest_framework.routers import DefaultRouter
from .views import ProdutoViewSet

router = DefaultRouter()
router.register(r'produtos', ProdutoViewSet, basename='produtos')

urlpatterns = router.urls
