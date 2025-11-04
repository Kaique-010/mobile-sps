from django.db import models


class Propriedades(models.Model):
    prop_empr = models.IntegerField('Empresa')
    prop_fili = models.IntegerField('Filial')
    prop_codi = models.IntegerField('Código', primary_key=True)
    prop_nome = models.CharField('Nome da Propriedade', max_length=100, blank=True, null=True)
    prop_hect = models.DecimalField('Hectares', max_digits=16, decimal_places=2, blank=True, null=True)
    prop_sigl = models.CharField('Sigla', max_length=20, blank=True, null=True)
    prop_data = models.DateField('Data', blank=True, null=True)
    prop_inat = models.BooleanField('Inativo', blank=True, null=True, default=False)

    class Meta:
        managed = False
        db_table = 'propriedades'
        verbose_name = 'Propriedade'
        verbose_name_plural = 'Propriedades'
        unique_together = (('prop_empr', 'prop_fili', 'prop_codi'),)

    def __str__(self):
        return f"{self.prop_nome or f'Propriedade {self.prop_codi}'}"


class DashboardCentroCustoAnual(models.Model):
    codigo = models.CharField(max_length=20, primary_key=True)
    expandido = models.CharField(max_length=50)
    grupo = models.CharField(max_length=50)
    nivel = models.IntegerField()
    nome = models.CharField(max_length=150)
    tipo = models.CharField(max_length=1)
    mes = models.CharField(max_length=50)
    mes_num = models.IntegerField()
    orcado = models.DecimalField(max_digits=15, decimal_places=2)
    realizado = models.DecimalField(max_digits=15, decimal_places=2)
    diferenca = models.DecimalField(max_digits=15, decimal_places=2)
    perc_execucao = models.DecimalField(max_digits=6, decimal_places=2)
    tem_filhos = models.BooleanField()
    codigo_pai = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'dashboardcentrocustoanual'
        verbose_name = "Dashboard Centro de Custo (Anual)"
        verbose_name_plural = "Dashboard Centros de Custo (Anual)"



STATUS_ORDEM = (
    (0, 'Aberto'),
    (1, 'Parcial'),
    (2, 'Faturada'),
    (3, 'Cancelada'),
)

###Ordem de Serviço Florestal
class Osflorestal(models.Model):
    osfl_empr = models.IntegerField()
    osfl_fili = models.IntegerField()
    osfl_orde = models.IntegerField(primary_key=True)
    osfl_data_aber = models.DateField(blank=True, null=True)
    osfl_hora_aber = models.TimeField(blank=True, null=True)
    osfl_forn = models.IntegerField(blank=True, null=True)
    osfl_stat = models.IntegerField(choices=STATUS_ORDEM, blank=True, null=True)
    osfl_situ = models.IntegerField(blank=True, null=True)
    osfl_obje = models.TextField(blank=True, null=True)
    osfl_func_terc_tipo = models.IntegerField(blank=True, null=True)
    osfl_func_terc = models.IntegerField(blank=True, null=True)
    osfl_prop = models.IntegerField(blank=True, null=True)
    osfl_com_peca = models.BooleanField(blank=True, null=True)
    osfl_com_serv = models.BooleanField(blank=True, null=True)
    osfl_com_fina = models.BooleanField(blank=True, null=True)
    osfl_libe_fatu = models.BooleanField(blank=True, null=True)
    osfl_data_entr = models.DateField(blank=True, null=True)
    osfl_data_fech = models.DateField(blank=True, null=True)
    osfl_desc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    osfl_outr = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    osfl_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    osfl_tota_hect = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    osfl_moti_canc = models.TextField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.

    class Meta:
        managed = False
        db_table = 'osflorestal'
        unique_together = (('osfl_empr', 'osfl_fili', 'osfl_orde'),)

    def calcular_total(self):
        """Calcula o total da ordem de serviço baseado nas peças e serviços"""
        from django.db.models import Sum
        from decimal import Decimal
        
        # Soma total das peças
        total_pecas = Osflorestalpecas.objects.filter(
            peca_empr=self.osfl_empr,
            peca_fili=self.osfl_fili,
            peca_orde=self.osfl_orde
        ).aggregate(total=Sum('peca_tota'))['total'] or Decimal('0')
        
        # Soma total dos serviços
        total_servicos = Osflorestalservicos.objects.filter(
            serv_empr=self.osfl_empr,
            serv_fili=self.osfl_fili,
            serv_orde=self.osfl_orde
        ).aggregate(total=Sum('serv_tota'))['total'] or Decimal('0')
        
        # Calcula o total geral
        total_geral = total_pecas + total_servicos
        
        # Aplica desconto se houver
        if self.osfl_desc:
            total_geral -= self.osfl_desc
            
        # Adiciona outros valores se houver
        if self.osfl_outr:
            total_geral += self.osfl_outr
            
        self.osfl_tota = total_geral
        return total_geral


class Osflorestalpecas(models.Model):
    peca_empr = models.IntegerField(primary_key=True)
    peca_fili = models.IntegerField()
    peca_orde = models.IntegerField()
    peca_item = models.IntegerField()
    peca_prod = models.CharField(max_length=20)
    peca_quan = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    peca_sobr = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    peca_unit = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    peca_tota = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    peca_hect = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    peca_desc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    peca_obse = models.TextField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.

    class Meta:
        managed = False
        db_table = 'osflorestalpecas'
        unique_together = (('peca_empr', 'peca_fili', 'peca_orde', 'peca_item'),)




class Osflorestalservicos(models.Model):
    serv_empr = models.IntegerField(primary_key=True)
    serv_fili = models.IntegerField()
    serv_orde = models.IntegerField()
    serv_item = models.IntegerField()
    serv_prod = models.CharField(max_length=20, blank=True, null=True)
    serv_quan = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    serv_unit = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    serv_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    serv_hect = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    serv_data = models.DateField(blank=True, null=True)
    serv_obse = models.TextField(blank=True, null=True)
    serv_desc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.

    class Meta:
        managed = False
        db_table = 'osflorestalservicos'
        unique_together = (('serv_empr', 'serv_fili', 'serv_orde', 'serv_item'),)