from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import api_router, web_router, views
from .views import whatsapp_webhook, webhook_verify, webhook_receive
import os

urlpatterns = [
    path("admin/", admin.site.urls),
    path("webhook/", whatsapp_webhook),
    path("webhook/verify/", webhook_verify),
    path("webhook/receive/", webhook_receive),
    


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

# Sempre servir estáticos do diretório local `static/` em ambiente de desenvolvimento
# Isso garante que CSS/JS/imagens funcionem mesmo quando STATIC_ROOT não foi coletado
urlpatterns += static(settings.STATIC_URL, document_root=os.path.join(settings.BASE_DIR, 'static'))