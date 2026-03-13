from django.urls import path

from sped.REST.viewsets import SpedViewSet

urlpatterns = [
    path("gerar/", SpedViewSet.as_view({"post": "gerar"}), name="sped-gerar"),
    path("preview/", SpedViewSet.as_view({"post": "preview"}), name="sped-preview"),
]
