from django.db import models

class OrcamentoAnaliticoView(models.Model):
    plan_redu = models.CharField(max_length=20)
    plan_nome = models.CharField(max_length=255)
    tipo = models.CharField(max_length=10, primary_key=True)
    mes = models.CharField(max_length=20)
    valor_orcado = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    valor_recebido = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    valor_pago = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    saldo = models.DecimalField(max_digits=15, decimal_places=2, null=True)


    class Meta:
        managed = False
        db_table = 'orcamento_2025'