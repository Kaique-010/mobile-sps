from django.urls import path
from .web_views import TitulosReceberListView

app_name = 'contas_a_receber_web'

# O slug é capturado no include do core/web_router.
urlpatterns = [
    path('', TitulosReceberListView.as_view(), name='titulos_receber_list'),
]