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