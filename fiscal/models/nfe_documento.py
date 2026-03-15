import json

from django.db import models


class NFeDocumento(models.Model):
    TIPO_CHOICES = [
        ("entrada", "Entrada"),
        ("saida", "Saída"),
    ]

    empresa = models.IntegerField(db_index=True)
    filial = models.IntegerField(db_index=True)

    chave = models.CharField(max_length=44, db_index=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)

    xml_original = models.TextField()
    json_normalizado = models.TextField()

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fiscal_nfe_documento"
        unique_together = ("empresa", "filial", "chave")
        indexes = [
            models.Index(fields=["empresa", "filial", "tipo"]),
            models.Index(fields=["empresa", "filial", "criado_em"]),
        ]

    def __str__(self):
        return f"{self.empresa}/{self.filial} {self.tipo} {self.chave}"

    @property
    def json_dict(self):
        try:
            return json.loads(self.json_normalizado or "{}")
        except Exception:
            return {}
