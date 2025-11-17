from .REST.urls import urlpatterns as rest_urlpatterns
from .Web.web_urls import urlpatterns as web_urlpatterns

urlpatterns = rest_urlpatterns + web_urlpatterns
