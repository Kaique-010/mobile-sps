from .models import WhatsAppWebhookEvent
from .parsers import WhatsAppOrderParser
from Pedidos.services.whats import CriarPedidoViaWhatsApp
 


def processar_evento(event_id):
    try:
        event = WhatsAppWebhookEvent.objects.get(id=event_id)
    except WhatsAppWebhookEvent.DoesNotExist:
        return JsonResponse({"error": "Evento não encontrado"}, status=404)

    body = event.payload
    value = body["entry"][0]["changes"][0]["value"]
    message = value["messages"][0]

    # Só processa pedidos
    if message.get("type") != "order":
        event.processed = True
        event.save()
        return

    parser = WhatsAppOrderParser()
    itens = parser.parse(message)

    # 📞 cria pedido no ERP
    CriarPedidoViaWhatsApp().executar({
        "cliente": message.get("from"),
        "itens": itens
    })
    # 📞 envia confirmação para o cliente
    CriarPedidoViaWhatsApp().envia_confirmacao(message.get("from"))

    event.processed = True
    event.save()