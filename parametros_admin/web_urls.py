from django.urls import path
from .web_views import ModulosListView, ModuloToggleView, ModulosSyncView

urlpatterns = [
    path('', ModulosListView.as_view(), name='parametros_admin_modulos'),
    path('toggle/<slug:modulo_slug>/', ModuloToggleView.as_view(), name='parametros_admin_toggle'),
    path('sync/', ModulosSyncView.as_view(), name='parametros_admin_sync'),
]
