from django.urls import path
from .web_views import ModulosListView, ModuloToggleView, ModulosSyncView, ParametrosListView, ParametroToggleView

urlpatterns = [
    path('', ModulosListView.as_view(), name='parametros_admin_modulos'),
    path('parametros/', ParametrosListView.as_view(), name='parametros_admin_parametros'),
    path('toggle/modulo/<slug:modulo_slug>/', ModuloToggleView.as_view(), name='parametros_admin_toggle_modulo'),
    path('toggle/parametro/<slug:parametro_slug>/', ParametroToggleView.as_view(), name='parametros_admin_toggle_parametro'),
    path('sync/', ModulosSyncView.as_view(), name='parametros_admin_sync'),
]
