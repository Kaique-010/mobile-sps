from django.urls import include, path
from GestaoObras.rest import urls as rest_urls

urlpatterns = [
    path("", include(rest_urls)),
]
