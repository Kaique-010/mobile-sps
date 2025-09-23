from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotaFiscalViewSet
from .emissao_views import EmissaoNFeViewSet

# Router para ViewSets
router = DefaultRouter()
router.register(r'notas-fiscais', NotaFiscalViewSet, basename='notafiscal')
router.register(r'emissao', EmissaoNFeViewSet, basename='emissao-nfe')

urlpatterns = [
    # URLs do router
    path('', include(router.urls)),
    
    # URLs personalizadas para acesso com chave composta
    path(
        'notas-fiscais/<int:empresa>/<int:filial>/<int:numero>/',
        NotaFiscalViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }),
        name='notafiscal-detail-composta'
    ),
    
    # URL para XML da NFe
    path(
        'notas-fiscais/<int:empresa>/<int:filial>/<int:numero>/xml/',
        NotaFiscalViewSet.as_view({'get': 'xml_nfe'}),
        name='notafiscal-xml'
    ),
    
    # URL para DANFE da NFe
    path(
        'notas-fiscais/<int:empresa>/<int:filial>/<int:numero>/danfe/',
        NotaFiscalViewSet.as_view({'get': 'danfe'}),
        name='notafiscal-danfe'
    ),
    
    # URL para dashboard
    path(
        'notas-fiscais/dashboard/',
        NotaFiscalViewSet.as_view({'get': 'dashboard'}),
        name='notafiscal-dashboard'
    ),
]