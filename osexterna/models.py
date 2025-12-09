from django.db import models

status_ordem = [
    (0, "Aberta"),
    (1, "Em assinatura"),
    (2, "Assinada"),
    (3, "Cancelada"),
    (4, "Finalizada"),
]



class Osexterna(models.Model):
    osex_empr = models.IntegerField(verbose_name='Empresa', db_column='osex_empr')
    osex_fili = models.IntegerField(verbose_name='Filial', db_column='osex_fili')
    osex_codi = models.IntegerField(primary_key=True, verbose_name='Código', db_column='osex_codi')
    osex_clie = models.IntegerField(blank=True, null=True, verbose_name='Cliente', db_column='osex_clie')
    osex_resp = models.IntegerField(blank=True, null=True, verbose_name='Responsável', db_column='osex_resp')
    osex_valo_tota = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, verbose_name='Valor Total', db_column='osex_valo_tota')
    osex_data_aber = models.DateField(blank=True, null=True, verbose_name='Data Abertura', db_column='osex_data_aber')
    osex_data_fech = models.DateField(blank=True, null=True, verbose_name='Data Fechamento', db_column='osex_data_fech')
    osex_canc_just = models.CharField(max_length=255, blank=True, null=True, verbose_name='Justificativa Cancelamento', db_column='osex_canc_just')
    osex_canc_usua = models.IntegerField(blank=True, null=True, verbose_name='Usuário Cancelamento', db_column='osex_canc_usua')
    osex_stat = models.IntegerField(blank=True, null=True, verbose_name='Status', db_column='osex_stat', choices=status_ordem)
    osex_usua = models.IntegerField(blank=True, null=True, verbose_name='Usuário', db_column='osex_usua')
    osex_ende = models.CharField(max_length=255, blank=True, null=True, verbose_name='Endereço', db_column='osex_ende')
    osex_ende_nume = models.CharField(max_length=10, blank=True, null=True, verbose_name='Número', db_column='osex_ende_nume')
    osex_bair = models.CharField(max_length=60, blank=True, null=True, verbose_name='Bairro', db_column='osex_bair')
    osex_cida = models.CharField(max_length=60, blank=True, null=True, verbose_name='Cidade', db_column='osex_cida')
    osex_clau = models.CharField(max_length=1, blank=True, null=True, verbose_name='Cláusula', db_column='osex_clau')
    osex_km_inic = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, verbose_name='Km Inicial', db_column='osex_km_inic')
    osex_km_tota = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, verbose_name='Km Total', db_column='osex_km_tota')
    osex_assi_clie = models.TextField(blank=True, null=True, verbose_name='Assinatura Cliente', db_column='osex_assi_clie')
    osex_assi_oper = models.TextField(blank=True, null=True, verbose_name='Assinatura Operador', db_column='osex_assi_oper')

    class Meta:
        managed = False
        db_table = 'osexterna'
        unique_together = (('osex_empr', 'osex_fili', 'osex_codi'),)




class Servicososexterna(models.Model):
    serv_empr = models.IntegerField()
    serv_fili = models.IntegerField()
    serv_desc = models.CharField(max_length=255, blank=True, null=True)
    serv_quan = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    serv_valo_unit = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    serv_valo_tota = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    serv_temp_esti = models.TimeField(blank=True, null=True)
    serv_os = models.IntegerField()
    serv_comp = models.TextField(blank=True, null=True)
    serv_sequ = models.IntegerField(primary_key=True)
    serv_conc = models.BooleanField(blank=True, null=True)
    serv_temp_util = models.TimeField(blank=True, null=True)
    serv_km_said = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    serv_km_cheg = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    serv_km_reto = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    serv_km_tota = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    serv_data_etap = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'servicososexterna'
        unique_together = (('serv_empr', 'serv_fili', 'serv_os', 'serv_sequ'),)

