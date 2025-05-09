from rest_framework.routers import DefaultRouter
from .views import ProdutoViewSet, UnidadeMedidaListView
from django.urls import path

router = DefaultRouter()
router.register(r'produtos', ProdutoViewSet, basename='produtos')

urlpatterns = [
    path('unidadesmedida/', UnidadeMedidaListView.as_view(), name='unidade-list'),
]

urlpatterns += router.urls  # junta tudo
