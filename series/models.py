from django.db import models

tipo_documento = (
    ('SA', 'Nota de Saída'),
    ('EN', 'Nota de Entrada'),
    ('FR', 'Fatura a Receber'),
    ('FP', 'Fatura a Pagar'),
    ('NC', 'Nota do Consumidor'),
    ('PR', 'Produtor Rural')
)

class Series(models.Model):
    seri_empr = models.IntegerField()
    seri_fili = models.IntegerField()
    seri_codi = models.CharField(max_length=3, primary_key=True)
    seri_nome = models.CharField(max_length=2, choices=tipo_documento)
    seri_docu = models.IntegerField(blank=True, null=True)
    

    class Meta:
        managed = False
        db_table = 'series'
        unique_together = (('seri_empr', 'seri_fili', 'seri_codi', 'seri_nome'),)