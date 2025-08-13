
from django.db import models



STATUS_ORCAMENTO = [
    (0, 'ABERTO'),
    (1, 'CANCELADO'),
    (2, 'EXPORTADO PEDIDO'),
   
]

class Orcamentopisos(models.Model):
    orca_empr = models.IntegerField(primary_key=True)
    orca_fili = models.IntegerField()
    orca_nume = models.IntegerField()
    orca_clie = models.IntegerField(blank=True, null=True)
    orca_data = models.DateField(blank=True, null=True)
    orca_tota = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    orca_obse = models.TextField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  
    orca_vend = models.IntegerField(blank=True, null=True)
    orca_stat = models.IntegerField(blank=True, null=True, choices=STATUS_ORCAMENTO, default=0)
    orca_moti_repr = models.CharField(max_length=225, blank=True, null=True)
    orca_pedi = models.IntegerField(blank=True, null=True)
    orca_desc = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    orca_fret = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    orca_ende = models.CharField(max_length=60, blank=True, null=True)
    orca_nume_ende = models.CharField(max_length=10, blank=True, null=True)
    orca_comp = models.CharField(max_length=100, blank=True, null=True)
    orca_bair = models.CharField(max_length=60, blank=True, null=True)
    orca_cida = models.CharField(max_length=60, blank=True, null=True)
    orca_esta = models.CharField(max_length=2, blank=True, null=True)
    orca_nome_reti = models.CharField(max_length=100, blank=True, null=True)
    orca_espe_reti = models.CharField(max_length=100, blank=True, null=True)
    orca_data_prev_entr = models.DateField(blank=True, null=True)
    orca_data_inst = models.DateField(blank=True, null=True)
    orca_data_entr_inst = models.DateField(blank=True, null=True)
    orca_mode_piso = models.CharField(max_length=500, blank=True, null=True)
    orca_mode_alum = models.CharField(max_length=500, blank=True, null=True)
    orca_mode_roda = models.CharField(max_length=500, blank=True, null=True)
    orca_mode_port = models.CharField(max_length=500, blank=True, null=True)
    orca_mode_outr = models.CharField(max_length=500, blank=True, null=True)
    orca_sent_piso = models.CharField(max_length=50, blank=True, null=True)
    orca_ajus_port = models.CharField(max_length=50, blank=True, null=True)
    orca_degr_esca = models.CharField(max_length=50, blank=True, null=True)
    orca_obra_habi = models.BooleanField(blank=True, null=True)
    orca_movi_mobi = models.BooleanField(blank=True, null=True)
    orca_remo_roda = models.BooleanField(blank=True, null=True)
    orca_remo_carp = models.BooleanField(blank=True, null=True)
    orca_croq_info = models.CharField(max_length=350, blank=True, null=True)
    orca_arqu = models.IntegerField(blank=True, null=True)
    orca_comi_arqu = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    orca_loja = models.IntegerField(blank=True, null=True)
    orca_obse_roma = models.CharField(max_length=500, blank=True, null=True)
    orca_fina = models.IntegerField(blank=True, null=True)
    usua_desc_codi = models.IntegerField(blank=True, null=True)
    orca_loca = models.CharField(max_length=1, blank=True, null=True)
    orca_tipo_cont_piso = models.CharField(max_length=1, blank=True, null=True)
    orca_umid = models.BooleanField(blank=True, null=True)
    orca_impo_pedi = models.IntegerField(blank=True, null=True)
    orca_codi_mens_fina = models.IntegerField(blank=True, null=True)
    orca_codi_mens_inst = models.IntegerField(blank=True, null=True)
    orca_mens_paga_mate = models.CharField(max_length=80, blank=True, null=True)
    orca_mens_metr = models.TextField(blank=True, null=True)
    orca_mens_mao_obra = models.CharField(max_length=80, blank=True, null=True)
    orca_comp_fone = models.CharField(max_length=20, blank=True, null=True)
    orca_cred = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orca_codi_maga = models.CharField(max_length=1, blank=True, null=True)
    orca_codi_hoop = models.CharField(max_length=20, blank=True, null=True)
    orca_taxa_cart = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'orcamentopisos'
        unique_together = (('orca_empr', 'orca_fili', 'orca_nume'),)




class Pedidospisos(models.Model):
    pedi_empr = models.IntegerField(primary_key=True)
    pedi_fili = models.IntegerField()
    pedi_nume = models.IntegerField()
    pedi_clie = models.IntegerField(blank=True, null=True)
    pedi_ende = models.CharField(max_length=60, blank=True, null=True)
    pedi_nume_ende = models.CharField(max_length=10, blank=True, null=True)
    pedi_comp = models.CharField(max_length=100, blank=True, null=True)
    pedi_bair = models.CharField(max_length=60, blank=True, null=True)
    pedi_cida = models.CharField(max_length=60, blank=True, null=True)
    pedi_esta = models.CharField(max_length=2, blank=True, null=True)
    pedi_nome_reti = models.CharField(max_length=100, blank=True, null=True)
    pedi_espe_reti = models.CharField(max_length=100, blank=True, null=True)
    pedi_data = models.DateField(blank=True, null=True)
    pedi_tota = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    pedi_obse = models.TextField(blank=True, null=True)
    pedi_vend = models.IntegerField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.
    pedi_stat = models.IntegerField(blank=True, null=True)
    pedi_orca = models.IntegerField(blank=True, null=True)
    pedi_fech = models.DateField(blank=True, null=True)
    pedi_form_paga = models.IntegerField(blank=True, null=True)
    pedi_data_prev_entr = models.DateField(blank=True, null=True)
    pedi_data_inst = models.DateField(blank=True, null=True)
    pedi_data_entr_inst = models.DateField(blank=True, null=True)
    pedi_mode_piso = models.CharField(max_length=500, blank=True, null=True)
    pedi_mode_alum = models.CharField(max_length=500, blank=True, null=True)
    pedi_mode_roda = models.CharField(max_length=500, blank=True, null=True)
    pedi_mode_port = models.CharField(max_length=500, blank=True, null=True)
    pedi_mode_outr = models.CharField(max_length=500, blank=True, null=True)
    pedi_sent_piso = models.CharField(max_length=50, blank=True, null=True)
    pedi_ajus_port = models.CharField(max_length=50, blank=True, null=True)
    pedi_degr_esca = models.CharField(max_length=50, blank=True, null=True)
    pedi_obra_habi = models.BooleanField(blank=True, null=True)
    pedi_movi_mobi = models.BooleanField(blank=True, null=True)
    pedi_remo_roda = models.BooleanField(blank=True, null=True)
    pedi_remo_carp = models.BooleanField(blank=True, null=True)
    pedi_croq_info = models.CharField(max_length=350, blank=True, null=True)
    pedi_desc = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    pedi_fret = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    pedi_nfev = models.IntegerField(blank=True, null=True)
    pedi_arqu = models.IntegerField(blank=True, null=True)
    pedi_comi_arqu = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    pedi_obse_roma = models.CharField(max_length=500, blank=True, null=True)
    pedi_fina = models.IntegerField(blank=True, null=True)
    usua_desc_codi = models.IntegerField(blank=True, null=True)
    pedi_forn = models.IntegerField(blank=True, null=True)
    pedi_loca = models.CharField(max_length=1, blank=True, null=True)
    pedi_tipo_cont_piso = models.CharField(max_length=1, blank=True, null=True)
    pedi_umid = models.BooleanField(blank=True, null=True)
    pedi_comp_fone = models.CharField(max_length=20, blank=True, null=True)
    pedi_moti_canc = models.TextField(blank=True, null=True)
    pedi_cred = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    pedi_clon = models.BooleanField(blank=True, null=True)
    pedi_taxa_cart = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'pedidospisos'
        unique_together = (('pedi_empr', 'pedi_fili', 'pedi_nume'),)





class Itensorcapisos(models.Model):
    item_empr = models.IntegerField(primary_key=True)
    item_fili = models.IntegerField()
    item_orca = models.IntegerField()
    item_ambi = models.IntegerField()
    item_prod = models.CharField(max_length=20)
    item_m2 = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    item_quan = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    item_unit = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    item_suto = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    item_obse = models.TextField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.
    item_nome_ambi = models.CharField(max_length=100, blank=True, null=True)
    item_nume = models.IntegerField(blank=True, null=True)
    item_caix = models.IntegerField(blank=True, null=True)
    item_desc = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    item_queb = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    item_inst_incl = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'itensorcapisos'
        unique_together = (('item_empr', 'item_fili', 'item_orca', 'item_ambi', 'item_prod'),)




class Itenspedidospisos(models.Model):
    item_empr = models.IntegerField(primary_key=True)
    item_fili = models.IntegerField()
    item_pedi = models.IntegerField()
    item_ambi = models.IntegerField()
    item_prod = models.CharField(max_length=20)
    item_m2 = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    item_quan = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    item_unit = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    item_suto = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    item_obse = models.TextField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.
    item_nome_ambi = models.CharField(max_length=100, blank=True, null=True)
    item_data_entr = models.DateField(blank=True, null=True)
    item_nume = models.IntegerField(blank=True, null=True)
    item_nfe_fatu = models.IntegerField(blank=True, null=True)
    item_nfe_entr = models.IntegerField(blank=True, null=True)
    item_comp_efet = models.DateField(blank=True, null=True)
    item_em_esto = models.BooleanField(blank=True, null=True)
    item_caix = models.IntegerField(blank=True, null=True)
    item_stat_manu = models.CharField(max_length=30, blank=True, null=True)
    item_desc = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    item_queb = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    item_stat_manu_data = models.DateField(blank=True, null=True)
    item_stat_manu_user = models.IntegerField(blank=True, null=True)
    item_prod_nome = models.CharField(max_length=100, blank=True, null=True)
    item_inst_incl = models.BooleanField(blank=True, null=True)
    item_quan_entr = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    item_caix_entr = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'itenspedidospisos'
        unique_together = (('item_empr', 'item_fili', 'item_pedi', 'item_ambi', 'item_prod'),)



