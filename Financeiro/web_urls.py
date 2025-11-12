from django.urls import path
from .web_views import FluxoCaixaView

app_name = "financeiro_web"

urlpatterns = [
    path("", FluxoCaixaView.as_view(), name="fluxo_de_caixa"),
]