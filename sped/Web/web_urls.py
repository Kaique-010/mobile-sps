from django.urls import path

from sped.Web.Views.gerarView import SpedGerarView

app_name = "sped_web"

urlpatterns = [
    path("", SpedGerarView.as_view(), name="gerar"),
]
