from django.urls import path
from .web_views import ModulosListView, ModuloToggleView, ModulosSyncView, ParametrosListView, ParametroToggleView

urlpatterns = [
    path('', ModulosListView.as_view(), name='parametros_admin_modulos'),
    path('parametros/', ParametrosListView.as_view(), name='parametros_admin_parametros'),
    path('toggle/<slug:parametro_slug>/', ParametroToggleView.as_view(), name='parametros_admin_toggle'),
    path('toggle/<slug:modulo_slug>/', ModuloToggleView.as_view(), name='parametros_admin_toggle'),
    path('sync/', ModulosSyncView.as_view(), name='parametros_admin_sync'),
]
