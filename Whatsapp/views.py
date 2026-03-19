from django.shortcuts import render

# Create your views here.
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.utils import get_db_from_slug
from .models import WhatsAppWebhookEvent
from .services import processar_evento
from .parsers import WhatsAppOrderParser    
from Licencas.models import Filiais



banco = get_db_from_slug()
TOKEN_DE_VERIFICACAO = Filiais.objects.using(banco).first().token_whatsapp


@csrf_exempt
def webhook_whatsapp(request):
    # 🔐 Validação inicial (Meta faz GET)
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == TOKEN_DE_VERIFICACAO:
            return JsonResponse(int(challenge), safe=False)

        return JsonResponse({"error": "Token inválido"}, status=403)

    # 📩 Recebimento de eventos
    if request.method == "POST":
        try:
            body = json.loads(request.body)

            # 🔑 Extrai ID único do evento
            entry = body.get("entry", [])
            if not entry:
                return JsonResponse({"status": "ignored"})

            changes = entry[0].get("changes", [])
            value = changes[0].get("value", {})
            messages = value.get("messages", [])

            if not messages:
                return JsonResponse({"status": "no_message"})

            message = messages[0]
            event_id = message.get("id")

            # 🧱 Idempotência
            if WhatsAppWebhookEvent.objects.filter(whats_even_id=event_id).exists():
                return JsonResponse({"status": "duplicate"})

            # 🔄 Persistência
            event = WhatsAppWebhookEvent.objects.create(
                whats_empr=value.get("empr"),
                whats_fili=value.get("fili"),
                whats_even_id=event_id,
                whats_payl=body
            )

            # 🔥 Processamento (ideal: async)
            processar_evento.delay(event.id)  # Celery
            # ou síncrono:
            # processar_evento(event.id)

            return JsonResponse({"status": "received"})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)