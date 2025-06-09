from django.db import models


class Os(models.Model):
    os_empr = models.IntegerField()
    os_fili = models.IntegerField()
    os_os = models.IntegerField(primary_key=True)
    os_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    os_data_aber = models.DateField()
    os_hora_aber = models.TimeField(blank=True, null=True)
    os_clie = models.IntegerField(blank=True, null=True)
    os_prof_aber = models.IntegerField(blank=True, null=True)
    os_fina_os = models.IntegerField(blank=True, null=True)
    os_obje_os = models.TextField(blank=True, null=True)
    os_fabr = models.IntegerField(blank=True, null=True)
    os_marc = models.IntegerField(blank=True, null=True)
    os_mode = models.IntegerField(blank=True, null=True)
    os_hori = models.DecimalField(max_digits=15, decimal_places=1, blank=True, null=True)
    os_plac = models.CharField(max_length=40, blank=True, null=True)
    os_pref = models.CharField(max_length=30, blank=True, null=True)
    os_cont = models.CharField(max_length=40, blank=True, null=True)
    os_prob_rela = models.TextField(blank=True, null=True)
    os_stat_os = models.IntegerField(blank=True, null=True)
    os_situ = models.IntegerField(blank=True, null=True)
    os_nota_peca = models.CharField(max_length=20, blank=True, null=True)
    os_nota_serv = models.CharField(max_length=100, blank=True, null=True)
    os_tem_peca = models.BooleanField(blank=True, null=True)
    os_tem_serv = models.BooleanField(blank=True, null=True)
    os_moti_canc = models.TextField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True) 
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True) 
    os_loca_apli = models.TextField(blank=True, null=True)
    os_ende_apli = models.TextField(blank=True, null=True)
    os_resp = models.IntegerField(blank=True, null=True)
    os_obse = models.TextField(blank=True, null=True)
    os_plac_1 = models.CharField(max_length=40, blank=True, null=True)
    os_data_entr = models.DateField(blank=True, null=True)
    os_data_fech = models.DateField(blank=True, null=True)
    os_desc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    os_auto = models.CharField(max_length=60, blank=True, null=True)
    os_praz_paga = models.CharField(max_length=100, blank=True, null=True)
    os_com_fina = models.BooleanField(blank=True, null=True)
    os_ja_proc = models.BooleanField(blank=True, null=True)
    os_rena = models.CharField(max_length=11, blank=True, null=True)
    os_chas = models.CharField(max_length=17, blank=True, null=True)
    os_moto = models.CharField(max_length=255, blank=True, null=True)
    os_fech_obse = models.TextField(blank=True, null=True)
    os_seto = models.IntegerField(blank=True, null=True)    

    class Meta:
        managed = False
        db_table = 'os'
        unique_together = (('os_empr', 'os_fili', 'os_os'),)
    
    def calcular_total(self):
            total_pecas = sum(
                peca.peca_tota or 0 
                for peca in PecasOs.objects.filter(
                    peca_empr=self.os_empr,
                    peca_fili=self.os_fili,
                    peca_os=self.os_os
                )
            )
            
            total_servicos = sum(
                servico.serv_tota or 0
                for servico in ServicosOs.objects.filter(
                    serv_empr=self.os_empr,
                    serv_fili=self.os_fili,
                    serv_os=self.os_os
                )
            )
            
            self.os_tota = total_pecas + total_servicos
            return self.os_tota


class PecasOs(models.Model):
    peca_empr = models.IntegerField()
    peca_fili = models.IntegerField()
    peca_os = models.IntegerField()
    peca_item = models.IntegerField(db_column='peca_item',primary_key=True)
    peca_prod = models.CharField(max_length=20, blank=True, null=True)
    peca_quan = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    peca_unit = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    peca_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    peca_data = models.DateField(blank=True, null=True)
    peca_prof = models.IntegerField(blank=True, null=True)
    peca_obse = models.TextField(blank=True, null=True)
    peca_moes = models.BooleanField(blank=True, null=True)
    peca_desc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.
    selecionado = models.BooleanField(blank=True, null=True)
    peca_perc_desc = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    peca_impr = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'pecasos'
        unique_together = (('peca_empr', 'peca_fili', 'peca_os', 'peca_item'),)
    



class ServicosOs(models.Model):
    serv_empr = models.IntegerField(primary_key=True)
    serv_fili = models.IntegerField()
    serv_os = models.IntegerField()
    serv_item = models.IntegerField()
    serv_prod = models.CharField(max_length=20, blank=True, null=True)
    serv_quan = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    serv_unit = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    serv_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    serv_data = models.DateField(blank=True, null=True)
    serv_prof = models.IntegerField(blank=True, null=True)
    serv_obse = models.TextField(blank=True, null=True)
    serv_desc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.
    serv_perc_desc = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    serv_impr = models.BooleanField(blank=True, null=True)
    serv_stat = models.IntegerField()
    serv_data_hora_impr = models.DateTimeField(blank=True, null=True)
    serv_stat_seto = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'servicosos'
        unique_together = (('serv_empr', 'serv_fili', 'serv_os', 'serv_item'),)