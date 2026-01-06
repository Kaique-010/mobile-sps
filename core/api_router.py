from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from Licencas.views import licencas_mapa, TokenRefreshCustomView

urlpatterns = [
    # Rotas públicas
    path("licencas/mapa/", licencas_mapa, name="licencas-mapa"),
    path("<slug>/entidades-login/", include("Entidades.urls")),

    # Auth
    path("<slug>/auth/token/refresh/", TokenRefreshCustomView.as_view(), name="token_refresh"),

    # Rotas principais (privadas)
    path("<slug>/licencas/", include("Licencas.urls")),
    path("<slug>/produtos/", include("Produtos.urls")),
    path("<slug>/entidades/", include("Entidades.urls")),
    path("<slug>/pedidos/", include("Pedidos.urls")),
    path("<slug>/orcamentos/", include("Orcamentos.urls")),
    path("<slug>/dashboards/", include("dashboards.urls")),
    path("<slug>/entradas_estoque/", include("Entradas_Estoque.urls")),
    path("<slug>/listacasamento/", include("listacasamento.urls")),
    path("<slug>/saidas_estoque/", include("Saidas_Estoque.urls")),
    path("<slug>/implantacao/", include("implantacao.urls")),
    path("<slug>/contas_a_pagar/", include("contas_a_pagar.urls")),
    path("<slug>/contas_a_receber/", include("contas_a_receber.urls")),
    path("<slug>/contratos/", include("contratos.urls")),
    path("<slug>/ordemdeservico/", include("OrdemdeServico.urls")),
    path("<slug>/caixadiario/", include("CaixaDiario.urls")),
    path("<slug>/Os/", include("O_S.urls")),
    path("<slug>/osexterna/", include("osexterna.urls")),
    path("<slug>/auditoria/", include("auditoria.urls")),
    path("<slug>/notificacoes/", include("notificacoes.urls")),
    path("<slug>/Sdk_recebimentos/", include("Sdk_recebimentos.urls")),
    path("<slug>/comissoes/", include("SpsComissoes.urls")),
    path("<slug>/enviar-cobranca/", include("EnvioCobranca.urls")),
    path("<slug>/dre/", include("DRE.urls")),
    path("<slug>/gerencial/", include("Gerencial.urls")),
    path("<slug>/ordemproducao/", include("OrdemProducao.urls")),
    path("<slug>/parametros-admin/", include("parametros_admin.urls")),
    path("<slug>/controledevisitas/", include("controledevisitas.urls")),
    path("<slug>/pisos/", include("Pisos.urls")),
    path("<slug>/mcp-agent/", include("mcp_agent_db.urls")),
    path("<slug>/coletaestoque/", include("coletaestoque.REST.urls")),
    path("<slug>/Floresta/", include("Floresta.urls")),
    path("<slug>/lctobancario/", include("Lancamentos_Bancarios.urls")),
    path("<slug>/notasfiscais/", include("Notas_Fiscais.urls")),
    path("<slug>/notasdestinadas/", include("NotasDestinadas.urls")),
    path("<slug>/notasdestinadas/", include("NotasDestinadas.urls")),
    path("<slug>/cfop/", include("CFOP.REST.urls")),
    path("<slug>/assistente/", include("Assistente_Spart.urls")),
    path("<slug>/ParametrosSps/", include("ParametrosSps.urls")),
    path("<slug>/boletos/", include("boletos.REST.urls")),
    path("<slug>/controledePonto/", include("controledePonto.Rest.urls")),

    # Documentação da API
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("schema/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-alt"),
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),

]
