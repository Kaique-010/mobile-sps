# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PropriedadesViewSet, fluxo_gerencial
from .views_osflorestal import OsViewSet, PecasOsViewSet, ServicosOsViewSet
from .views_financeiro import GerarTitulosOS, RemoverTitulosOSView, ConsultarTitulosOSView

router = DefaultRouter()
router.register(r'propriedades', PropriedadesViewSet, basename='propriedades')
router.register(r'osflorestal', OsViewSet, basename='osflorestal')
router.register(r'pecas-os', PecasOsViewSet, basename='pecas-os')
router.register(r'servicos-os', ServicosOsViewSet, basename='servicos-os')

urlpatterns = router.urls + [
    path('fluxo-gerencial/', fluxo_gerencial, name='fluxo-gerencial'),
    path('osflorestal/gerar-titulos/', GerarTitulosOS.as_view(), name='gerar-titulos-os'),
    path('osflorestal/remover-titulos/', RemoverTitulosOSView.as_view(), name='remover-titulos-os'),
    path('osflorestal/consultar-titulos/', ConsultarTitulosOSView.as_view(), name='consultar-titulos-os'),
]