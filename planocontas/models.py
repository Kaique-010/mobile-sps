from django.db import models


class Planodecontas(models.Model):
    plan_empr = models.IntegerField(primary_key=True)
    plan_redu = models.IntegerField()
    plan_niv1 = models.IntegerField(blank=True, null=True)
    plan_expa = models.CharField(max_length=60, blank=True, null=True)
    plan_grup = models.CharField(max_length=60, blank=True, null=True)
    plan_nive = models.IntegerField(blank=True, null=True)
    plan_anal = models.CharField(max_length=1, blank=True, null=True)
    plan_natu = models.CharField(max_length=2, blank=True, null=True)
    plan_refe = models.CharField(max_length=60, blank=True, null=True)
    plan_dati = models.DateField(blank=True, null=True)
    plan_data = models.DateField(blank=True, null=True)
    plan_inat = models.BooleanField(blank=True, null=True)
    plan_data_inat = models.DateField(blank=True, null=True)
    plan_obse = models.TextField(blank=True, null=True)
    plan_nome = models.CharField(max_length=60, blank=True, null=True)
    plan_dre = models.CharField(max_length=2, blank=True, null=True)
    plan_natu_sped = models.CharField(max_length=2, blank=True, null=True)
    plan_flu1 = models.CharField(max_length=1, blank=True, null=True)
    plan_flu2 = models.IntegerField(blank=True, null=True)
    plan_de = models.IntegerField(blank=True, null=True)
    plan_acer_comb = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'planodecontas'
        unique_together = (('plan_empr', 'plan_redu'),)

    def __str__(self):
        return f"{self.plan_empr} - {self.plan_redu} - {self.plan_nome}"
    

class Indicesrazao(models.Model):
    indr_empr = models.IntegerField(primary_key=True)
    indr_fili = models.IntegerField()
    indr_lote = models.CharField(max_length=10)
    indr_sequ = models.IntegerField()
    indr_cont = models.IntegerField()
    indr_cecu = models.IntegerField(blank=True, null=True)
    indr_dbcr = models.CharField(max_length=1, blank=True, null=True)
    indr_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    indr_data = models.DateField(blank=True, null=True)
    indr_cont_part = models.IntegerField(blank=True, null=True)
    indr_expa = models.CharField(max_length=60, blank=True, null=True)
    indr_lanc_zera = models.BooleanField(blank=True, null=True)
    indr_enti = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'indicesrazao'
        unique_together = (('indr_empr', 'indr_fili', 'indr_lote', 'indr_sequ', 'indr_cont'),)
        
    def __str__(self):
        return f"{self.indr_empr} - {self.indr_fili} - {self.indr_lote} - {self.indr_sequ} - {self.indr_cont}"