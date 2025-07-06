
from django.db import models

class ComissaoSps(models.Model): 
    comi_id = models.AutoField(primary_key=True)
    comi_empr = models.IntegerField()
    comi_fili = models.IntegerField()
    comi_func = models.CharField(max_length=255)  # ID do funcionário
    comi_func_nome = models.CharField(max_length=100, blank=True, null=True)  # Nome do funcionário
    comi_clie = models.CharField(max_length=255)  # ID do cliente
    comi_clie_nome = models.CharField(max_length=100, blank=True, null=True)  # Nome do cliente
    comi_cate = models.CharField(max_length=50, choices=[
        ('1', 'Melhoria'),
        ('2', 'Implantação'),
        ('3', 'Dashboards'),
        ('4', 'Mobile'),
        ('5', 'Vendas'),
    ])
    comi_valo_tota = models.DecimalField(max_digits=12, decimal_places=2)
    comi_impo = models.DecimalField(max_digits=12, decimal_places=2)
    comi_valo_liqu = models.DecimalField(max_digits=12, decimal_places=2)
    comi_perc = models.DecimalField(max_digits=5, decimal_places=2)
    comi_comi_tota = models.DecimalField(max_digits=12, decimal_places=2)
    comi_parc = models.IntegerField()
    comi_comi_parc = models.DecimalField(max_digits=12, decimal_places=2)
    comi_form_paga = models.CharField(max_length=20)
    comi_data_entr = models.DateField()

    class Meta:
        managed = False
        db_table = 'comissoes_sps'

