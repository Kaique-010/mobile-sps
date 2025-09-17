from django.db import models

class Lctobancario(models.Model):
    laba_empr = models.IntegerField()
    laba_fili = models.IntegerField()
    laba_banc = models.IntegerField()
    laba_ctrl = models.IntegerField(primary_key=True)
    laba_data = models.DateField(blank=True, null=True)
    laba_tire = models.IntegerField(blank=True, null=True)
    laba_cont = models.IntegerField(blank=True, null=True)
    laba_cecu = models.IntegerField(blank=True, null=True)
    laba_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    laba_even = models.IntegerField(blank=True, null=True)
    laba_soci = models.CharField(max_length=20, blank=True, null=True)
    laba_codi_hist = models.IntegerField(blank=True, null=True)
    laba_hist = models.TextField(blank=True, null=True)
    laba_lote = models.CharField(max_length=10, blank=True, null=True)
    laba_ctrl_ctb = models.IntegerField(blank=True, null=True)
    laba_dbcr = models.CharField(max_length=1, blank=True, null=True)
    laba_nume_mens = models.IntegerField(blank=True, null=True)
    laba_enti = models.IntegerField(blank=True, null=True)
    laba_cheq = models.IntegerField(blank=True, null=True)
    laba_data_comp = models.DateField(blank=True, null=True)
    laba_cheq_comp = models.BooleanField(blank=True, null=True)
    laba_data_bomp = models.DateField(blank=True, null=True)
    laba_nomi = models.CharField(max_length=65, blank=True, null=True)
    laba_inte = models.BooleanField(blank=True, null=True)
    laba_desc_pont = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    laba_ctrl_paga = models.IntegerField(blank=True, null=True)
    laba_ctrc_rece = models.IntegerField(blank=True, null=True)
    laba_soli_adto = models.IntegerField(blank=True, null=True)
    laba_mens_feri = models.BooleanField(blank=True, null=True)
    laba_dife_depe = models.BooleanField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.
    laba_pag_for = models.BooleanField(blank=True, null=True)
    laba_audi = models.BooleanField(blank=True, null=True)
    laba_audi_data = models.DateField(blank=True, null=True)
    laba_audi_por = models.IntegerField(blank=True, null=True)
    laba_data_reci = models.DateField(blank=True, null=True)
    laba_via_reci = models.IntegerField(blank=True, null=True)
    laba_tiop = models.IntegerField(blank=True, null=True)
    laba_prat = models.IntegerField(blank=True, null=True)
    lanc_proj_resp_paga = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lctobancario'
        unique_together = (('laba_empr', 'laba_fili', 'laba_banc', 'laba_ctrl'),)