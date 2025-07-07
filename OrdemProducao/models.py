
from django.db import models


class Ordemprodfotos(models.Model):
    orpr_codi = models.IntegerField(primary_key=True)  
    orpr_empr = models.IntegerField()
    orpr_fili = models.IntegerField()
    orpr_nume_foto = models.IntegerField()
    orpr_desc_foto = models.TextField(blank=True, null=True)
    orpr_foto_ante = models.BinaryField(blank=True, null=True)
    orpr_foto_atua = models.BinaryField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ordemprodfotos'
        unique_together = (('orpr_codi', 'orpr_empr', 'orpr_fili', 'orpr_nume_foto'),)


class Ordemproditens(models.Model):
    orpr_codi = models.IntegerField(primary_key=True)  
    orpr_empr = models.IntegerField()  # Campo que estava faltando
    orpr_fili = models.IntegerField()
    orpr_pedi = models.IntegerField()
    orpr_item = models.IntegerField()
    orpr_prod = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ordemproditens'
        unique_together = (('orpr_codi', 'orpr_empr', 'orpr_fili', 'orpr_pedi', 'orpr_item'),)


class Ordemprodmate(models.Model):
    orpm_orpr = models.IntegerField(primary_key=True)  # The composite primary key (orpm_orpr, orpm_codi) found, that is not supported. The first column is selected.
    orpm_codi = models.IntegerField()
    orpm_prod = models.CharField(max_length=20, blank=True, null=True)
    orpm_quan = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    orpm_unit = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    orpm_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpm_med1 = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpm_med2 = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpm_med3 = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpm_qdme = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpm_qdmt = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    orpm_cust = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpm_lkst = models.CharField(max_length=6, blank=True, null=True)
    orpm_esto = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpm_totv = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ordemprodmate'
        unique_together = (('orpm_orpr', 'orpm_codi'),)


class Ordemprodetapa(models.Model):
    opet_orpr = models.IntegerField(primary_key=True)  # The composite primary key (opet_orpr, opet_codi) found, that is not supported. The first column is selected.
    opet_codi = models.IntegerField()
    opet_desc = models.CharField(max_length=1000, blank=True, null=True)
    opet_func = models.IntegerField(blank=True, null=True)
    opet_dati = models.DateField(blank=True, null=True)
    opet_datf = models.DateField(blank=True, null=True)
    opet_equi = models.IntegerField(blank=True, null=True)
    opet_etap = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ordemprodetapa'
        unique_together = (('opet_orpr', 'opet_codi'),)
  

class Ordemproducao(models.Model):
    tipo_ordem = [
        ('1', 'Confecção'),
        ('2', 'Conserto'),
        ('3', 'Orçamento'),
        ('4', 'Conserto Relógio'),
    ]
    
    orpr_codi = models.AutoField(primary_key=True)
    orpr_entr = models.DateTimeField()
    orpr_fech = models.DateTimeField(blank=True, null=True)
    orpr_daen = models.DateTimeField(blank=True, null=True)
    orpr_nuca = models.CharField(unique=True, max_length=6)
    orpr_clie = models.IntegerField()
    orpr_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpr_prev = models.DateTimeField()
    orpr_empr = models.IntegerField(db_column='orpr_empr', default=1)
    orpr_fili = models.IntegerField(default=1)
    orpr_tipo = models.CharField(max_length=100, choices=tipo_ordem, default='Confecção')
    orpr_gara = models.BooleanField()
    orpr_vend = models.IntegerField()  
    orpr_desc = models.TextField(blank=True, null=True)
    orpr_stat = models.IntegerField(default=1)
    orpr_prod = models.CharField(max_length=20, blank=True, null=True)
    orpr_quan = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    orpr_gram_clie = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    orpr_cort = models.BooleanField()

    def __str__(self):
        return str(self.orpr_clie)

    class Meta:
       
        db_table = 'ordemproducao'
