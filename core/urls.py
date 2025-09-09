# core/urls.py
from django.contrib import admin
from rest_framework_simplejwt.views import TokenRefreshView
from django.urls import path, include
from Licencas.views import LoginView, licencas_mapa  
from django.contrib import admin
from django.urls import path, include
from Licencas.views import licencas_mapa
from . import views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


urlpatterns = [
    path('', views.index, name='index'),
    # Endpoint de health para Docker
    path('health/', views.health_check, name='health'),
    path('api/warm-cache/', views.warm_cache_endpoint, name='warm_cache'),
    
    # Rota pública (sem slug)
    path('api/licencas/mapa/', licencas_mapa, name='licencas-mapa'),
    # Nova rota pública para login de clientes
    path('api/<slug>/entidades-login/', include('Entidades.urls')),

    # Rotas privadas (com slug automático)
    path('api/<slug>/licencas/', include('Licencas.urls')),
    path('api/<slug>/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    #rotas dos Apps
    path('api/<slug>/produtos/', include('Produtos.urls')),
    path('api/<slug>/entidades/', include('Entidades.urls')),
    path('api/<slug>/pedidos/', include('Pedidos.urls')),
    path('api/<slug>/orcamentos/', include('Orcamentos.urls')),
    path('api/<slug:slug>/dashboards/', include('dashboards.urls')),
    path('api/<slug>/entradas_estoque/', include('Entradas_Estoque.urls')),
    path('api/<slug>/listacasamento/', include('listacasamento.urls')),
    path('api/<slug>/saidas_estoque/', include('Saidas_Estoque.urls')),
    path('api/<slug>/implantacao/', include('implantacao.urls')),
    path('api/<slug>/contas_a_pagar/', include('contas_a_pagar.urls')),
    path('api/<slug>/contas_a_receber/', include('contas_a_receber.urls')),
    path('api/<slug>/contratos/', include('contratos.urls')),
    path('api/<slug>/ordemdeservico/', include('OrdemdeServico.urls')),
    path('api/<slug>/caixadiario/', include('CaixaDiario.urls')),
    path('api/<slug>/Os/', include('O_S.urls')),
    path('api/<slug>/auditoria/', include('auditoria.urls')),
    path('api/<slug>/notificacoes/', include('notificacoes.urls')),
    path('api/<slug>/Sdk_recebimentos/', include('Sdk_recebimentos.urls')),
    path('api/<slug>/comissoes/', include('SpsComissoes.urls')),
    path('api/<slug>/enviar-cobranca/', include('EnvioCobranca.urls')),
    path('api/<slug>/dre/', include('DRE.urls')),
    #path('api/<slug>/gerencial/', include('Gerencial.urls')),
    path('api/<slug>/ordemproducao/', include('OrdemProducao.urls')),
    path('api/<slug:slug>/parametros-admin/', include('parametros_admin.urls')),
    path('api/<slug>/controledevisitas/', include('controledevisitas.urls')),
    path('api/<slug>/pisos/', include('Pisos.urls')),
    
    
    # MCP Agent DB - Nova rota adicionada
    path('api/<slug>/mcp-agent/', include('mcp_agent_db.urls')),
    
    
    # Rotas de documentação do DRF-Spectacular
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
