from django.urls import path
from .views import PerfilPermissaoView, recursos_api, verificar_api, sincronizar_api
from .views import PerfisListView
from .views import perfis_defaults_api
from .views import aplicar_defaults_api
from .views import bootstrap_api

urlpatterns = [
    path('', PerfisListView.as_view(), name='perfil_list'),
    path('<int:perfil_id>/permissoes/', PerfilPermissaoView.as_view(), name='perfil_permissoes'),
    path('api/recursos/', recursos_api, name='perfil_recursos_api'),
    path('api/verificar/', verificar_api, name='perfil_verificar_api'),
    path('api/sincronizar/', sincronizar_api, name='perfil_sincronizar_api'),
    path('api/perfis-defaults/', perfis_defaults_api, name='perfil_defaults_api'),
    path('api/aplicar-defaults/<int:perfil_id>/', aplicar_defaults_api, name='perfil_aplicar_defaults_api'),
    path('api/bootstrap/', bootstrap_api, name='perfil_bootstrap_api'),
]
