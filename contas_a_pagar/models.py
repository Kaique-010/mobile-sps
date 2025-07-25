from django.db import models

class Titulospagar(models.Model):
    titu_empr = models.IntegerField()
    titu_fili = models.IntegerField()
    titu_forn = models.IntegerField()
    titu_titu = models.CharField(max_length=13, primary_key=True)
    titu_seri = models.CharField(max_length=5)
    titu_parc = models.CharField(max_length=4)
    titu_emis = models.DateField(blank=True, null=True)
    titu_venc = models.DateField(blank=True, null=True)
    titu_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    titu_cont = models.IntegerField(blank=True, null=True)
    titu_cecu = models.IntegerField(blank=True, null=True)
    titu_even = models.IntegerField(blank=True, null=True)
    titu_prov = models.BooleanField(blank=True, null=True)
    titu_hist = models.TextField(blank=True, null=True)
    titu_aber = models.CharField(max_length=1, default='A')
    titu_lote = models.CharField(max_length=10, blank=True, null=True)
    titu_ctrl = models.IntegerField(blank=True, null=True)
    titu_coba = models.CharField(max_length=100, blank=True, null=True)
    titu_desc_ao_dia = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    titu_desc_ao_dia_perc = models.BooleanField(blank=True, null=True)
    titu_desc_ao_dia_vlr = models.BooleanField(blank=True, null=True)
    titu_desc_pont = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    titu_desc_pont_perc = models.BooleanField(blank=True, null=True)
    titu_desc_pont_vlr = models.BooleanField(blank=True, null=True)
    titu_dias_prot = models.IntegerField(blank=True, null=True)
    titu_mult = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    titu_mult_perc = models.BooleanField(blank=True, null=True)
    titu_mult_vlr = models.BooleanField(blank=True, null=True)
    titu_juro = models.DecimalField(max_digits=17, decimal_places=4, blank=True, null=True)
    titu_juro_perc = models.BooleanField(blank=True, null=True)
    titu_juro_vlr = models.BooleanField(blank=True, null=True)
    titu_gera_parc = models.BooleanField(blank=True, null=True)
    titu_port = models.IntegerField(blank=True, null=True)
    titu_situ = models.IntegerField(blank=True, null=True)
    titu_inte = models.BooleanField(blank=True, null=True)
    titu_pag_for = models.BooleanField(blank=True, null=True)
    titu_tipo_pag_for = models.IntegerField(blank=True, null=True)
    titu_banc_pag_for = models.CharField(max_length=3, blank=True, null=True)
    titu_agen_pag_for = models.CharField(max_length=11, blank=True, null=True)
    titu_diag_pag_for = models.CharField(max_length=2, blank=True, null=True)
    titu_cont_pag_for = models.CharField(max_length=11, blank=True, null=True)
    titu_dico_pag_for = models.CharField(max_length=2, blank=True, null=True)
    titu_coco_pag_for = models.BooleanField(blank=True, null=True)
    titu_fatu_cte = models.BooleanField(blank=True, null=True)
    titu_form_reci = models.CharField(max_length=2, blank=True, null=True)
    titu_fatu = models.BooleanField(blank=True, null=True)
    titu_nume_fatu = models.IntegerField(blank=True, null=True)
    titu_tipo_oper = models.IntegerField(blank=True, null=True)
    titu_paga_nao_cont = models.BooleanField(blank=True, null=True)
    titu_nomi = models.CharField(max_length=60, blank=True, null=True)
    titu_aler = models.TextField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True) 
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True) 
    titu_audi = models.BooleanField(blank=True, null=True)
    titu_audi_data = models.DateField(blank=True, null=True)
    titu_audi_por = models.IntegerField(blank=True, null=True)
    titu_tipo = models.CharField(max_length=7, blank=True, null=True)
    titu_id_nota_fisc = models.IntegerField(blank=True, null=True)
    titu_lote_cont = models.CharField(max_length=10, blank=True, null=True)
    titu_lanc_debi_cont = models.IntegerField(blank=True, null=True)
    titu_lanc_cred_cont_1 = models.IntegerField(blank=True, null=True)
    titu_lanc_cred_cont_2 = models.IntegerField(blank=True, null=True)
    titu_lanc_juro_cont = models.IntegerField(blank=True, null=True)
    titu_id_nfe = models.IntegerField(blank=True, null=True)
    titu_debi_capi = models.IntegerField(blank=True, null=True)
    titu_cred_capi = models.IntegerField(blank=True, null=True)
    titu_debi_juro = models.IntegerField(blank=True, null=True)
    titu_cred_juro = models.IntegerField(blank=True, null=True)
    titu_debi_capi_paga = models.IntegerField(blank=True, null=True)
    titu_debi_juro_paga = models.IntegerField(blank=True, null=True)
    titu_valo_capi = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    titu_valo_juro = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    titu_apro_dda = models.BooleanField(blank=True, null=True)
    titu_nume_apro = models.IntegerField(blank=True, null=True)
    titu_nume_dda = models.IntegerField(blank=True, null=True)
    titu_refe_comp = models.CharField(max_length=30, blank=True, null=True)
    titu_km = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    titu_litr = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    titu_prat = models.IntegerField(blank=True, null=True)
    titu_diar = models.BooleanField(blank=True, null=True)
    titu_gera_auto = models.BooleanField(blank=True, null=True)
    titu_proj_resp_paga = models.IntegerField(blank=True, null=True)
    titu_usua_lanc = models.CharField(max_length=60, blank=True, null=True)


    class Meta:
        managed = False
        db_table = 'titulospagar'
        unique_together = (('titu_empr', 'titu_fili', 'titu_forn', 'titu_titu', 'titu_seri', 'titu_parc', 'titu_emis', 'titu_venc'),)



class Bapatitulos(models.Model):
    bapa_sequ = models.IntegerField(primary_key=True)
    bapa_ctrl = models.IntegerField()
    bapa_empr = models.IntegerField()
    bapa_fili = models.IntegerField()
    bapa_forn = models.IntegerField()
    bapa_titu = models.CharField(max_length=13, db_column='bapa_titu')
    bapa_seri = models.CharField(max_length=5, blank=True, null=True)
    bapa_parc = models.CharField(max_length=4, blank=True, null=True)
    bapa_dpag = models.DateField(blank=True, null=True)
    bapa_apag = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bapa_vmul = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bapa_vjur = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bapa_vdes = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bapa_pago = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bapa_topa = models.CharField(max_length=1, blank=True, null=True)
    bapa_lote_valo = models.CharField(max_length=10, blank=True, null=True)
    bapa_ctrl_valo = models.IntegerField(blank=True, null=True)
    bapa_lote_mult = models.CharField(max_length=10, blank=True, null=True)
    bapa_ctrl_mult = models.IntegerField(blank=True, null=True)
    bapa_lote_juro = models.CharField(max_length=10, blank=True, null=True)
    bapa_ctrl_juro = models.IntegerField(blank=True, null=True)
    bapa_lote_desc = models.CharField(max_length=10, blank=True, null=True)
    bapa_ctrl_desc = models.IntegerField(blank=True, null=True)
    bapa_banc = models.IntegerField(blank=True, null=True)
    bapa_cheq = models.IntegerField(blank=True, null=True)
    bapa_bpar = models.DateField(blank=True, null=True)
    bapa_hist = models.TextField(blank=True, null=True)
    bapa_pjur = models.DecimalField(max_digits=7, decimal_places=4, blank=True, null=True)
    bapa_pmul = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    bapa_pdes = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    bapa_juro_aodi = models.BooleanField(blank=True, null=True)
    bapa_desc_aodi = models.BooleanField(blank=True, null=True)
    bapa_nomi = models.CharField(max_length=65, blank=True, null=True)
    bapa_form = models.CharField(max_length=1, blank=True, null=True)
    bapa_valo_pago = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bapa_sub_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bapa_emis = models.DateField(blank=True, null=True)
    bapa_venc = models.DateField(blank=True, null=True)
    bapa_cont = models.IntegerField(blank=True, null=True)
    bapa_cecu = models.IntegerField(blank=True, null=True)
    bapa_even = models.IntegerField(blank=True, null=True)
    bapa_port = models.IntegerField(blank=True, null=True)
    bapa_situ = models.IntegerField(blank=True, null=True)
    bapa_ctrl_banc = models.IntegerField(blank=True, null=True)
    bapa_lote_banc = models.CharField(max_length=10, blank=True, null=True)
    bapa_sequ_banc = models.IntegerField(blank=True, null=True)
    bapa_dive = models.BooleanField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.
    bapa_tipo_paga = models.IntegerField(blank=True, null=True)
    bapa_audi = models.BooleanField(blank=True, null=True)
    bapa_audi_data = models.DateField(blank=True, null=True)
    bapa_audi_por = models.IntegerField(blank=True, null=True)
    bapa_id_adto = models.IntegerField(blank=True, null=True)
    bapa_lote_cont = models.CharField(max_length=10, blank=True, null=True)
    bapa_lanc_cont_long = models.IntegerField(blank=True, null=True)
    bapa_refe_comp = models.CharField(max_length=30, blank=True, null=True)
    bapa_lote_desp = models.CharField(max_length=10, blank=True, null=True)
    bapa_ctrl_desp = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bapatitulos'