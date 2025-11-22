from django.urls import path, include

urlpatterns = [
    path("web/", include("boletos.web.urls")),
    path("api/", include("boletos.api.urls")),
]
