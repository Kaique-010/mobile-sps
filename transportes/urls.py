from django.urls import path, include
from rest_framework.routers import DefaultRouter

from transportes.views import web
from transportes.views import api
from transportes.views import regras

app_name = 'transportes'

# Router para API
router = DefaultRouter()
router.register(r'ctes', api.CteViewSet, basename='api-cte')

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),

    # Web URLs
    path('web/ctes/', web.CteListView.as_view(), name='cte_list'),
    path('web/ctes/novo/', web.CteCreateView.as_view(), name='cte_create'),
    
    # Abas de Edição
    path('web/ctes/<int:pk>/emissao/', web.CteEmissaoView.as_view(), name='cte_emissao'),
    path('web/ctes/<int:pk>/tipo/', web.CteTipoView.as_view(), name='cte_tipo'),
    path('web/ctes/<int:pk>/rota/', web.CteRotaView.as_view(), name='cte_rota'),
    path('web/ctes/<int:pk>/seguro/', web.CteSeguroView.as_view(), name='cte_seguro'),
    path('web/ctes/<int:pk>/carga/', web.CteCargaView.as_view(), name='cte_carga'),
    path('web/ctes/<int:pk>/tributacao/', web.CteTributacaoView.as_view(), name='cte_tributacao'),
    
    # Ações
    path('web/ctes/<int:pk>/excluir/', web.CteDeleteView.as_view(), name='cte_delete'),
    path('web/ctes/<int:pk>/emitir/', web.CteEmitirView.as_view(), name='cte_emitir'),
    path('web/ctes/<int:pk>/consultar-recibo/', web.CteConsultarReciboView.as_view(), name='cte_consultar_recibo'),

    # Regras ICMS
    path('web/regras/', regras.RegraICMSListView.as_view(), name='regra_list'),
    path('web/regras/nova/', regras.RegraICMSCreateView.as_view(), name='regra_create'),
    path('web/regras/<int:pk>/editar/', regras.RegraICMSUpdateView.as_view(), name='regra_update'),
    path('web/regras/<int:pk>/excluir/', regras.RegraICMSDeleteView.as_view(), name='regra_delete'),
]
