from django.urls import path
from . import web_views

app_name = "centrosdecustos"

urlpatterns = [
    path("", web_views.CentrodeCustosListView.as_view(), name="lista"),
    path("novo/", web_views.CentrodeCustosCreateView.as_view(), name="criar"),
    path("editar/<int:cecu_redu>/", web_views.CentrodeCustosUpdateView.as_view(), name="editar"),
    path("excluir/<int:cecu_redu>/", web_views.CentrodeCustosDeleteView.as_view(), name="excluir"),
    path("exportar/", web_views.ExportarCentrodeCustosView.as_view(), name="exportar"),
    path("proximo-codigo/", web_views.ProximoCodigoCentrodeCustosView.as_view(), name="proximo_codigo"),
]