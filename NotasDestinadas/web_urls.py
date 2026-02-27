from django.urls import path
from .web_views import NotasDestinadasListView, NotasManuaisListView, NotaManualCreateView, NotaManualDetailView

urlpatterns = [
    path('', NotasDestinadasListView.as_view(), name='notas_destinadas_web'),
    path(
        'manuais/lista/',
        NotasManuaisListView.as_view(),
        name='notas-manuais-lista'
    ),
    path(
        'manuais/nova/',
        NotaManualCreateView.as_view(),
        name='nota-manual-nova'
    ),
    path(
        'manuais/<int:nota_id>/edit/',
        NotaManualCreateView.as_view(),
        name='nota-manual-edit'
    ),
    path(
        'manuais/<int:nota_id>/detalhe/',
        NotaManualDetailView.as_view(),
        name='nota-manual-detalhe'
    ),
]
