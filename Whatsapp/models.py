from django.db import models


class WhatsAppWebhookEvent(models.Model):
    whats_empr = models.CharField(max_length=255)
    whats_fili = models.CharField(max_length=255)
    whats_even_id = models.CharField(max_length=255, unique=True)
    whats_payl = models.JSONField()
    whats_proc = models.BooleanField(default=False)
    whats_cria = models.DateTimeField(auto_now_add=True)
