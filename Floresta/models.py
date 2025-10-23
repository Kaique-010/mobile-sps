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
    nivel = models.IntegerField()
    nome = models.CharField(max_length=150)
    tipo = models.CharField(max_length=1)
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