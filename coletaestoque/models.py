from django.db import models
from Licencas.models import Usuarios


class ColetaEstoque(models.Model):
    cole_prod = models.CharField(max_length=50, help_text="Código do produto")
    cole_quan_lida = models.DecimalField(max_digits=10, decimal_places=2)
    cole_data_leit = models.DateTimeField(auto_now_add=True)
    cole_usua = models.ForeignKey(Usuarios, on_delete=models.CASCADE, related_name='coletas_estoque') 
    cole_empr = models.IntegerField(help_text="Empresa da coleta", default=1)
    cole_fili= models.IntegerField(help_text="Filial da coleta", default=1)
    cole_processado = models.BooleanField(default=False, help_text="Indica se a coleta foi processada")
    cole_data_processamento = models.DateTimeField(null=True, blank=True, help_text="Data do processamento")

    class Meta:
        db_table = 'coletas_estoque'
        verbose_name = 'Coleta de Estoque'
        verbose_name_plural = 'Coletas de Estoque'

    def __str__(self):
        return f'Coleta de {self.cole_prod} ({self.cole_quan_lida}) em {self.cole_data_leit.strftime("%Y-%m-%d %H:%M")}'
