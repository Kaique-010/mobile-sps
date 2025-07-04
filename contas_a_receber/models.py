from django.db import models


FORMA_RECEBIMENTO = [
    ('00', 'DUPLICATA'),
    ('01', 'CHEQUE'),
    ('02', 'PROMISSÓRIA'),
    ('03', 'RECIBO'),
    ('50', 'CHEQUE PRÉ'),
    ('51', 'CARTÃ DE CRÉDITO'),
    ('52', 'CARTÃ DE DÉBITO'),
    ('53', 'BOLETO BANCÁRIO'),
    ('54', 'DINHEIRO'),
    ('55', 'DEPÓSITO EM CONTA'),
    ('56', 'VENDA À VISTA '),
    ('60', 'PIX'),
]

class Titulosreceber(models.Model):
    titu_empr = models.IntegerField()
    titu_fili = models.IntegerField()
    titu_clie = models.IntegerField()
    titu_titu = models.CharField(max_length=13, primary_key=True)
    titu_seri = models.CharField(max_length=5)
    titu_parc = models.CharField(max_length=3)
    titu_emis = models.DateField(blank=True, null=True)
    titu_venc = models.DateField(blank=True, null=True)
    titu_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    titu_cont = models.IntegerField(blank=True, null=True, default=0)
    titu_cecu = models.IntegerField(blank=True, null=True)
    titu_even = models.IntegerField(blank=True, null=True)
    titu_prov = models.BooleanField(blank=True, null=True)
    titu_hist = models.TextField(blank=True, null=True)
    titu_aber = models.CharField(max_length=1, blank=True, null=True, default='A')
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
    titu_juro = models.DecimalField(max_digits=15, decimal_places=3, blank=True, null=True)
    titu_juro_perc = models.BooleanField(blank=True, null=True)
    titu_juro_vlr = models.BooleanField(blank=True, null=True)
    titu_gera_parc = models.BooleanField(blank=True, null=True)
    titu_port = models.IntegerField(blank=True, null=True)
    titu_situ = models.IntegerField(blank=True, null=True)
    titu_inte = models.BooleanField(blank=True, null=True)
    titu_form_reci = models.CharField(max_length=2, choices=FORMA_RECEBIMENTO, blank=True, null=True, default='54')
    titu_noss_nume = models.CharField(max_length=30, blank=True, null=True)
    titu_nome_arqu = models.CharField(max_length=100, blank=True, null=True)
    titu_nume_arqu = models.IntegerField(blank=True, null=True)
    titu_data_reme = models.DateField(blank=True, null=True)
    titu_usua_reme = models.CharField(max_length=60, blank=True, null=True)
    titu_noss_nume_form = models.CharField(max_length=50, blank=True, null=True)
    titu_fatu = models.BooleanField(blank=True, null=True)
    titu_nume_fatu = models.IntegerField(blank=True, null=True)
    titu_tipo_oper = models.IntegerField(blank=True, null=True)
    titu_aler = models.TextField(blank=True, null=True)
    titu_vend = models.IntegerField(blank=True, null=True)
    titu_perc_comi = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    titu_vlr_desc_parc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    titu_valo_comi = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  
    titu_vend_proc = models.BooleanField(blank=True, null=True)
    titu_audi = models.BooleanField(blank=True, null=True)
    titu_audi_data = models.DateField(blank=True, null=True)
    titu_audi_por = models.IntegerField(blank=True, null=True)
    titu_plac = models.CharField(max_length=7, blank=True, null=True)
    titu_cte = models.IntegerField(blank=True, null=True)
    titu_seri_cte = models.CharField(max_length=3, blank=True, null=True)
    titu_nota = models.TextField(blank=True, null=True)
    titu_peso = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    titu_tari = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    titu_cobr_elet = models.BooleanField(blank=True, null=True)
    titu_cobr_banc = models.IntegerField(blank=True, null=True)
    titu_cobr_cart = models.IntegerField(blank=True, null=True)
    titu_tipo = models.CharField(max_length=7, blank=True, null=True)
    titu_id_adto = models.IntegerField(blank=True, null=True)
    titu_valo_orig = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    titu_venc_orig = models.DateField(blank=True, null=True)
    titu_peri_inic = models.DateField(blank=True, null=True)
    titu_peri_fina = models.DateField(blank=True, null=True)
    titu_nume_reci = models.IntegerField(blank=True, null=True)
    titu_ende = models.IntegerField(blank=True, null=True)
    titu_seu_nume = models.CharField(max_length=30, blank=True, null=True)
    titu_seu_nume_form = models.CharField(max_length=30, blank=True, null=True)
    titu_prot_cart = models.CharField(max_length=20, blank=True, null=True)
    titu_valo_comi_vend = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    titu_titu_orig = models.CharField(max_length=13, blank=True, null=True)
    titu_seri_orig = models.CharField(max_length=5, blank=True, null=True)
    titu_nume_orig_cont = models.CharField(max_length=13, blank=True, null=True)
    titu_seri_orig_cont = models.CharField(max_length=5, blank=True, null=True)
    titu_cont_fatu = models.BooleanField(blank=True, null=True)
    titu_nfse_rps = models.IntegerField(blank=True, null=True)
    titu_nfse_nota = models.CharField(max_length=20, blank=True, null=True)
    titu_prat = models.IntegerField(blank=True, null=True)
    titu_chav_api = models.CharField(max_length=32, blank=True, null=True)
    titu_gera_auto = models.BooleanField(blank=True, null=True)
    titu_codi_prot_naci = models.IntegerField(blank=True, null=True)
    titu_linh_digi = models.CharField(max_length=255, blank=True, null=True)
    titu_url_bole = models.CharField(max_length=255, blank=True, null=True)
    titu_gera_prot = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'titulosreceber'
        unique_together = (('titu_empr', 'titu_fili', 'titu_clie', 'titu_titu', 'titu_seri', 'titu_parc'), ('titu_empr', 'titu_fili', 'titu_noss_nume_form', 'titu_cobr_banc', 'titu_cobr_cart'),)
        
        
        
        
        

class Baretitulos(models.Model):
    bare_sequ = models.IntegerField(primary_key=True)
    bare_ctrl = models.IntegerField()
    bare_empr = models.IntegerField()
    bare_fili = models.IntegerField()
    bare_clie = models.IntegerField()
    bare_titu = models.CharField(max_length=13, db_column='bare_titu')
    bare_seri = models.CharField(max_length=5, blank=True, null=True)
    bare_parc = models.CharField(max_length=3, blank=True, null=True)
    bare_dpag = models.DateField(blank=True, null=True)
    bare_apag = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bare_vmul = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bare_vjur = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bare_vdes = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bare_pago = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bare_topa = models.CharField(max_length=1, blank=True, null=True)
    bare_lote_valo = models.CharField(max_length=10, blank=True, null=True)
    bare_ctrl_valo = models.IntegerField(blank=True, null=True)
    bare_lote_mult = models.CharField(max_length=10, blank=True, null=True)
    bare_ctrl_mult = models.IntegerField(blank=True, null=True)
    bare_lote_juro = models.CharField(max_length=10, blank=True, null=True)
    bare_ctrl_juro = models.IntegerField(blank=True, null=True)
    bare_lote_desc = models.CharField(max_length=10, blank=True, null=True)
    bare_ctrl_desc = models.IntegerField(blank=True, null=True)
    bare_banc = models.IntegerField(blank=True, null=True)
    bare_cheq = models.IntegerField(blank=True, null=True)
    bare_bpar = models.DateField(blank=True, null=True)
    bare_hist = models.TextField(blank=True, null=True)
    bare_pjur = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    bare_pmul = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    bare_pdes = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    bare_juro_aodi = models.BooleanField(blank=True, null=True)
    bare_desc_aodi = models.BooleanField(blank=True, null=True)
    bare_nomi = models.CharField(max_length=40, blank=True, null=True)
    bare_form = models.CharField(max_length=1, blank=True, null=True)
    bare_valo_pago = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bare_sub_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bare_emis = models.DateField(blank=True, null=True)
    bare_venc = models.DateField(blank=True, null=True)
    bare_cont = models.IntegerField(blank=True, null=True)
    bare_cecu = models.IntegerField(blank=True, null=True)
    bare_even = models.IntegerField(blank=True, null=True)
    bare_port = models.IntegerField(blank=True, null=True)
    bare_situ = models.IntegerField(blank=True, null=True)
    bare_ctrl_banc = models.IntegerField(blank=True, null=True)
    bare_lote_banc = models.CharField(max_length=10, blank=True, null=True)
    bare_sequ_banc = models.IntegerField(blank=True, null=True)
    bare_dive = models.BooleanField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.
    bare_audi = models.BooleanField(blank=True, null=True)
    bare_audi_data = models.DateField(blank=True, null=True)
    bare_audi_por = models.IntegerField(blank=True, null=True)
    bare_nota_fisc = models.CharField(max_length=10, blank=True, null=True)
    bare_seri_fisc = models.CharField(max_length=3, blank=True, null=True)
    bare_mode_fisc = models.CharField(max_length=3, blank=True, null=True)
    bare_emis_fisc = models.DateField(blank=True, null=True)
    bare_id_adto = models.IntegerField(blank=True, null=True)
    bare_id_adto_func = models.IntegerField(blank=True, null=True)
    bare_prot_cart = models.CharField(max_length=20, blank=True, null=True)
    bare_rece_arqu = models.CharField(max_length=50, blank=True, null=True)
    bare_usua_baix = models.IntegerField(blank=True, null=True)
    bare_usua_nome = models.CharField(max_length=60, blank=True, null=True)
    bare_data_baix = models.DateField(blank=True, null=True)
    bare_vend = models.IntegerField(blank=True, null=True)
    bare_titu_comi = models.CharField(max_length=13, blank=True, null=True)
    bare_seri_comi = models.CharField(max_length=5, blank=True, null=True)
    bare_parc_comi = models.CharField(max_length=3, blank=True, null=True)
    bare_cred = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bare_vend1 = models.IntegerField(blank=True, null=True)
    bare_vend2 = models.IntegerField(blank=True, null=True)
    bare_vend3 = models.IntegerField(blank=True, null=True)
    bare_comi1 = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    bare_comi2 = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    bare_comi3 = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    bare_valo_ipi = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bare_data_pedi = models.DateField(blank=True, null=True)
    bare_valo_comi = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bare_nume_pedi = models.IntegerField(blank=True, null=True)
    bare_tota_pedi = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bare_vmul_nfse = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'baretitulos'