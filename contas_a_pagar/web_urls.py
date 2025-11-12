from django.urls import path
from .web_views import TitulosPagarListView

app_name = 'contas_a_pagar_web'

# O slug é capturado no include do core/web_router.
urlpatterns = [
    path('', TitulosPagarListView.as_view(), name='titulos_pagar_list'),
]