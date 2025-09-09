from channels.routing import ProtocolTypeRouter, URLRouter
# Seus consumidores de WebSocket serão importados aqui no futuro
# from . import consumers

# A lista de rotas de WebSocket (pode ficar vazia por enquanto)
websocket_urlpatterns = [
    # re_path(r'ws/notificacoes/$', consumers.NotificationConsumer.as_asgi()),
]

# Este é o objeto 'application' que estava faltando
application = ProtocolTypeRouter({
    'websocket': URLRouter(
        websocket_urlpatterns
    ),
})
