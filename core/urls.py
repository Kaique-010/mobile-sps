from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import api_router, web_router, views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Health e cache
    path("health/", views.health_check, name="health"),
    path("api/warm-cache/", views.warm_cache_endpoint, name="warm_cache"),

    # Rotas principais
    path("", views.index, name="index"),
    path("api/", include(api_router)),
    path("web/", include(web_router)),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)