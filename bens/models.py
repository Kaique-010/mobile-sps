from django.db import models


class Bensptr(models.Model):
    bens_empr = models.IntegerField(primary_key=True)
    bens_fili = models.IntegerField()
    bens_codi = models.CharField(max_length=13)
    bens_desc = models.TextField(blank=True, null=True)
    bens_forn = models.IntegerField(blank=True, null=True)
    bens_nota = models.CharField(max_length=44, blank=True, null=True)
    bens_grup = models.IntegerField(blank=True, null=True)
    bens_marc = models.CharField(max_length=30, blank=True, null=True)
    bens_mode = models.CharField(max_length=30, blank=True, null=True)
    bens_seri = models.CharField(max_length=30, blank=True, null=True)
    bens_data_aqui = models.DateField(blank=True, null=True)
    bens_valo_aqui = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bens_praz_vida = models.IntegerField(blank=True, null=True)
    bens_inic_depr = models.DateField(blank=True, null=True)
    bens_depr_ano = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    bens_depr_mes = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    bens_depr_dia = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    bens_data_baix = models.DateField(blank=True, null=True)
    bens_moti = models.IntegerField(blank=True, null=True)
    bens_depr_real = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bens_cust = models.BooleanField(blank=True, null=True)
    bens_depr = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bens_obse = models.TextField(blank=True, null=True)
    bens_cecu = models.IntegerField(blank=True, null=True)
    bens_item_nota = models.IntegerField(blank=True, null=True)
    bens_seri_nota = models.CharField(max_length=3, blank=True, null=True)
    bens_emis_nota = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bensptr'
        unique_together = (('bens_empr', 'bens_fili', 'bens_codi'),)

class Grupobens(models.Model):
    grup_empr = models.IntegerField(primary_key=True)
    grup_codi = models.IntegerField()
    grup_nome = models.CharField(max_length=60, blank=True, null=True)
    grup_vida_util = models.IntegerField(blank=True, null=True)
    grup_perc_depr_ano = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    grup_perc_depr_mes = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    grup_perc_depr_dia = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'grupobens'
        unique_together = (('grup_empr', 'grup_codi'),)


class Motivosptr(models.Model):
    moti_codi = models.IntegerField(primary_key=True)
    moti_desc = models.CharField(max_length=60, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'motivosptr'