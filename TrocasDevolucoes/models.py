from django.db import models


TDVL_STATUS = [
    ('0', 'Rascunho'),
    ('1', 'Processando'),
    ('2', 'Concluída'),
    ('3', 'Cancelada'),
]

TDVL_TIPO = [
    ('TROC', 'Troca'),
    ('DEVO', 'Devolução'),
]


class TrocaDevolucao(models.Model):
    tdvl_empr = models.IntegerField()
    tdvl_fili = models.IntegerField()
    tdvl_nume = models.IntegerField(primary_key=True)
    tdvl_pdor = models.IntegerField(help_text='Pedido de origem')
    tdvl_clie = models.CharField(max_length=60)
    tdvl_vend = models.CharField(max_length=15, blank=True, null=True)
    tdvl_data = models.DateField()
    tdvl_tipo = models.CharField(max_length=4, choices=TDVL_TIPO, default='DEVO')
    tdvl_stat = models.CharField(max_length=4, choices=TDVL_STATUS, default='0')
    tdvl_tode = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tdvl_tore = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tdvl_safi = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tdvl_obse = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'trocas_devolucoes'
        managed = True
        unique_together = ('tdvl_empr', 'tdvl_fili', 'tdvl_nume')


class ItensTrocaDevolucao(models.Model):
    itdv_empr = models.IntegerField()
    itdv_fili = models.IntegerField()
    itdv_tdvl = models.IntegerField(help_text='Número da troca/devolução')
    itdv_item = models.IntegerField()
    itdv_pdor = models.IntegerField(help_text='Pedido de origem')
    itdv_itor = models.IntegerField(help_text='Item do pedido de origem')
    itdv_pror = models.CharField(max_length=60, help_text='Produto origem')
    itdv_qtor = models.DecimalField(max_digits=15, decimal_places=5, default=0)
    itdv_prre = models.CharField(max_length=60, blank=True, null=True, help_text='Produto reposição')
    itdv_qtre = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    itdv_vlor = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    itdv_vlre = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    itdv_moti = models.CharField(max_length=120, blank=True, null=True)

    class Meta:
        db_table = 'itens_trocas_devolucoes'
        managed = True
        unique_together = ('itdv_empr', 'itdv_fili', 'itdv_tdvl', 'itdv_item')
