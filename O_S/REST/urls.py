from rest_framework import routers
from django.urls import path
from .views import *
from .view_enviar_email import EnviarEmail
from .view_enviar_whats import EnviarWhatsapp
from ..views_financeiro import (
    GerarTitulosOS, 
    RemoverTitulosOSView,
    ConsultarTitulosOSView,
    AtualizarTituloOSView
)
from ..view_dash import OrdemServicoGeralViewSet

router = routers.DefaultRouter()
router.register(r'ordens', OsViewSet, basename='ordens')
router.register(r'pecas', PecasOsViewSet, basename='pecas')
router.register(r'servicos', ServicosOsViewSet, basename='servicos')
router.register(r'os-geral', OrdemServicoGeralViewSet, basename='os-geral')
router.register(r'os-hora', OsHoraViewSet, basename='os-hora')

urlpatterns = []

urlpatterns += [
    path('ordens/patch/', OsViewSet.as_view({'patch': 'patch_ordem', 'post': 'patch_ordem'}), name='ordens-patch'),
    path('ordens/enviaremail/', EnviarEmail.as_view(), name='enviar_email_ordens'),
    path('ordens/enviarwhatsapp/', EnviarWhatsapp.as_view(), name='enviar_whatsapp_ordens'),    
    path('produtos/mega/', MegaProdutosView.as_view(), name='produtos-mega'),
    path('entidades/mega/', MegaEntidadesApiView.as_view(), name='entidades-mega'),
]

# Adiciona as rotas padrão do router após a rota explícita
urlpatterns += router.urls

# Rotas Financeiras
urlpatterns += [
    path('financeiro/gerar-titulos/', GerarTitulosOS.as_view(), name='gerar_titulos'),
    path('financeiro/remover-titulos/', RemoverTitulosOSView.as_view(), name='remover_titulos'),
    path('financeiro/consultar-titulos/<int:orde_nume>/', ConsultarTitulosOSView.as_view(), name='consultar_titulos'),
    path('financeiro/atualizar-titulo/', AtualizarTituloOSView.as_view(), name='atualizar_titulo'),

]
