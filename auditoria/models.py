from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import JSONField

class LogAcao(models.Model):
    TIPO_ACAO_CHOICES = [
        ('GET', 'Consulta'),
        ('POST', 'Criação'),
        ('PUT', 'Atualização'),
        ('PATCH', 'Atualização Parcial'),
        ('DELETE', 'Exclusão'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    data_hora = models.DateTimeField(auto_now_add=True)
    tipo_acao = models.CharField(max_length=10, choices=TIPO_ACAO_CHOICES)
    url = models.TextField()
    ip = models.GenericIPAddressField(null=True)
    navegador = models.CharField(max_length=255)
    dados = JSONField(null=True)
    empresa = models.CharField(max_length=100, null=True, db_index=True)
    licenca = models.CharField(max_length=100, null=True, db_index=True)

    class Meta:
        db_table = 'auditoria_logacao'
        ordering = ['-data_hora']
        verbose_name = 'Log de Ação'
        verbose_name_plural = 'Logs de Ações'
        indexes = [
            models.Index(fields=['empresa', 'licenca', 'data_hora']),
            models.Index(fields=['usuario', 'data_hora']),
        ]

    def __str__(self):
        return f"{self.empresa} - {self.usuario} - {self.get_tipo_acao_display()} - {self.data_hora}"

    @property
    def acao_formatada(self):
        return self.get_tipo_acao_display()