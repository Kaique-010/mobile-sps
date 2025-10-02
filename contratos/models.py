from django.db import models


class Contratosvendas(models.Model):
    cont_empr = models.IntegerField()
    cont_fili = models.IntegerField()
    cont_cont = models.IntegerField(primary_key=True)
    cont_data = models.DateField(blank=True, null=True)
    cont_clie = models.IntegerField(blank=True, null=True)
    cont_perm_alte_clie = models.BooleanField(blank=True, null=True)
    cont_prod = models.CharField(max_length=20, blank=True, null=True)
    cont_info_adic = models.TextField(blank=True, null=True)
    cont_quan = models.DecimalField(max_digits=15, decimal_places=3, blank=True, null=True)
    cont_unit = models.DecimalField(max_digits=15, decimal_places=6, blank=True, null=True)
    cont_perm_alte_unit = models.BooleanField(blank=True, null=True)
    cont_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    cont_entr = models.DecimalField(max_digits=15, decimal_places=3, blank=True, null=True)
    cont_sald = models.DecimalField(max_digits=15, decimal_places=3, blank=True, null=True)
    cont_cst_icms = models.CharField(max_length=3, blank=True, null=True)
    cont_redu_icms = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cont_aliq_icms = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cont_cst_pis = models.CharField(max_length=2, blank=True, null=True)
    cont_aliq_pis = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cont_cst_cofi = models.CharField(max_length=2, blank=True, null=True)
    cont_aliq_cofi = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cont_cfop_esta = models.IntegerField(blank=True, null=True)
    cont_cfop_fora = models.IntegerField(blank=True, null=True)
    cont_venc = models.DateField(blank=True, null=True)
    cont_desc = models.CharField(max_length=60, blank=True, null=True)
    cont_port = models.IntegerField(blank=True, null=True)
    cont_situ = models.IntegerField(blank=True, null=True)
    cont_perm_alte_venc = models.BooleanField(blank=True, null=True)
    cont_form = models.CharField(max_length=2, blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', auto_now_add=True)  
    field_log_time = models.TimeField(db_column='_log_time', auto_now_add=True) 
    cont_sem_fina = models.BooleanField(blank=True, null=True)
    cont_tipo_fret = models.IntegerField(blank=True, null=True)
    cont_tran = models.IntegerField(blank=True, null=True)
    cont_veic = models.IntegerField(blank=True, null=True)
    cont_cont_orig = models.CharField(max_length=20, blank=True, null=True)
    cont_cond_fina = models.IntegerField(blank=True, null=True)
    cont_pedi_nume = models.CharField(max_length=15, blank=True, null=True)
    cont_pedi_item = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'contratosvendas'
        unique_together = (('cont_empr', 'cont_fili', 'cont_cont'),)
        ordering = ('-cont_cont','-cont_data')
        
    def __str__(self):
        return f"Empresa{self.cont_empr}/Filial{self.cont_fili}/Contrato{self.cont_cont}/Data{self.cont_data}"
