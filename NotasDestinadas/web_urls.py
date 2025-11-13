from django.urls import path
from .web_views import NotasDestinadasListView

urlpatterns = [
    path('', NotasDestinadasListView.as_view(), name='notas_destinadas_web'),
]
