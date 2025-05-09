from django.db import models

    

class SaidasEstoque(models.Model):
    said_sequ = models.IntegerField()
    said_empr = models.IntegerField(default=1)
    said_fili = models.IntegerField(default=1)
    said_prod = models.CharField(db_column='said_prod', primary_key=True, max_length=10)
    said_enti = models.CharField(db_column='said_enti', max_length=10, blank=True, null=True)
    said_data = models.DateField()
    said_quan = models.DecimalField(max_digits=10, decimal_places=2)
    said_tota = models.DecimalField(max_digits=10, decimal_places=2)
    said_obse = models.CharField(max_length=100, blank=True, null=True)
    said_usua = models.IntegerField()

    class Meta:
        db_table = 'saidasestoque'
        ordering = ['-said_data']
        constraints = [
            models.UniqueConstraint(fields=['said_empr', 'said_fili', 'said_prod', 'said_data'], name='pk_saida_estoque')
        ]

    def __str__(self):
        return f'Saída {self.said_prod} - {self.said_data}'
