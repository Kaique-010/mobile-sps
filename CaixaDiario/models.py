from django.db import models


class Caixageral(models.Model):
    caix_empr = models.IntegerField()
    caix_fili = models.IntegerField()
    caix_caix = models.IntegerField()
    caix_data = models.DateField(primary_key=True)
    caix_hora = models.TimeField(auto_now_add=True)
    caix_aber = models.CharField(max_length=1)
    caix_oper = models.IntegerField()
    caix_ecf = models.CharField(max_length=30, blank=True, null=True)
    caix_orig = models.IntegerField(blank=True, null=True)
    caix_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    caix_ctrl = models.IntegerField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True) 
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True) 
    caix_fech_data = models.DateField(blank=True, null=True)
    caix_fech_hora = models.TimeField(blank=True, null=True)
    caix_obse_fech = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'caixageral'
        unique_together = (('caix_empr', 'caix_fili', 'caix_caix', 'caix_data', 'caix_aber', 'caix_oper'),)



TIPO_MOVIMENTO = [
    ('1', 'DINHEIRO'),
    ('2', 'CHEQUE'),
    ('3', 'CARTÃO DE CREDITO'),
    ('4', 'CARTÃO DE DEBITO'),
    ('5', 'CREDIÁRIO'),
    ('6', 'PIX'),
   
]


class Movicaixa(models.Model):
    movi_empr = models.IntegerField(primary_key=True)
    movi_fili = models.IntegerField()
    movi_caix = models.IntegerField()
    movi_data = models.DateField()
    movi_ctrl = models.IntegerField("Controle",)
    movi_entr = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    movi_said = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    movi_tipo = models.IntegerField("Tipo de Movimento",choices=TIPO_MOVIMENTO)
    movi_obse = models.TextField(blank=True, null=True)
    movi_oper = models.IntegerField(blank=True, null=True)
    movi_hora = models.TimeField(blank=True, null=True)
    movi_nume_vend = models.IntegerField("Pedido de Venda",blank=True, null=True)
    movi_clie = models.IntegerField("Cliente",blank=True, null=True)
    movi_vend = models.IntegerField("Vendedor",blank=True, null=True)
    movi_cont = models.IntegerField(blank=True, null=True)
    movi_even = models.IntegerField(blank=True, null=True)
    movi_cecu = models.IntegerField(blank=True, null=True)
    movi_cheq = models.IntegerField(blank=True, null=True)
    movi_nomi = models.CharField(max_length=40, blank=True, null=True)
    movi_bomp = models.DateField(blank=True, null=True)
    movi_titu = models.CharField("Titulo",max_length=13, blank=True, null=True)
    movi_seri = models.CharField("Serie",max_length=5, blank=True, null=True, default='CAI')
    movi_parc = models.CharField(max_length=4, blank=True, null=True)
    movi_cheq_banc = models.IntegerField(blank=True, null=True)
    movi_cheq_agen = models.CharField(max_length=15, blank=True, null=True)
    movi_cheq_cont = models.CharField(max_length=15, blank=True, null=True)
    movi_seri_nota = models.CharField(max_length=3, blank=True, null=True)
    movi_nume_nota = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    movi_coo = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    movi_seri_ecf = models.CharField(max_length=20, blank=True, null=True)
    movi_codi_admi = models.IntegerField(blank=True, null=True)
    movi_tipo_movi = models.IntegerField(blank=True, null=True)
    movi_banc_tran = models.IntegerField(blank=True, null=True)
    movi_sequ_tran = models.IntegerField(blank=True, null=True)
    movi_sang = models.BooleanField(blank=True, null=True)
    movi_vend_orig = models.IntegerField(blank=True, null=True)
    movi_docu_fisc = models.IntegerField(blank=True, null=True)
    movi_bare_ctrl = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'movicaixa'
        unique_together = (('movi_empr', 'movi_fili', 'movi_caix', 'movi_data', 'movi_ctrl'),)