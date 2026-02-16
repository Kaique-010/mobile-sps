from django.db import models


TIPO_ADIANTAMENTO = (
    ('P', 'PAGAR'),
    ('R', 'RECEBER'),
)

class Adiantamentos(models.Model):
    adia_empr = models.IntegerField(primary_key=True)
    adia_fili = models.IntegerField()
    adia_enti = models.IntegerField()
    adia_docu = models.IntegerField()
    adia_ctrl = models.CharField(max_length=4, blank=True, null=True, verbose_name='Controle Adiantamento')
    adia_seri = models.CharField(max_length=3)
    adia_tipo = models.CharField(max_length=1, choices=TIPO_ADIANTAMENTO, default='P')
    adia_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Valor Adiantamento')
    adia_util = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Valor Utilizado')
    adia_sald = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Saldo Adiantamento')
    adia_obse = models.TextField(blank=True, null=True, verbose_name='Observação')
    adia_banc = models.IntegerField(blank=True, null=True, verbose_name='Banco')
    adia_ctrl_banc = models.IntegerField(blank=True, null=True, verbose_name='Controle Bancário')

    class Meta:
        managed = False
        db_table = 'adiantamentos'
        unique_together = (('adia_empr', 'adia_fili', 'adia_enti', 'adia_docu', 'adia_seri'),)