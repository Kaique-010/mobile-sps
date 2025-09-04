from django.db import models
from django.core.exceptions import ValidationError
from datetime import datetime

def validate_data_entrada(value):
    if value and value.year < 1900:
        raise ValidationError('Data deve ser posterior a 1900')

class EntradaEstoque(models.Model):
    entr_sequ = models.IntegerField(primary_key=True)
    entr_empr = models.IntegerField(default=1)
    entr_fili = models.IntegerField(default=1)
    entr_prod = models.CharField(db_column='entr_prod', max_length=10)
    entr_enti = models.CharField(db_column='entr_enti', max_length=10, blank=True, null=True)
    entr_data = models.DateField(db_column='entr_data', validators=[validate_data_entrada])
    entr_quan = models.DecimalField(max_digits=10, decimal_places=2)
    entr_tota = models.DecimalField(max_digits=10, decimal_places=2)
    entr_obse = models.CharField(max_length=100, blank=True, null=True)
    entr_usua = models.IntegerField()
    entr_lote_vend = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'entradasestoque'
        ordering = ['entr_sequ']
        verbose_name = 'Entrada Estoque'
        verbose_name_plural = 'Entradas Estoque'
        unique_together = (('entr_empr', 'entr_fili', 'entr_prod', 'entr_data'),) 

    def __str__(self):
        return f'Entrada {self.entr_prod} - {self.entr_data}'
