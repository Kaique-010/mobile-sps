from django.db import models

# Create your models here.
class RegistroPonto(models.Model):
    colaborador_id = models.IntegerField()
    documento = models.CharField(max_length=20)
    data_hora = models.DateTimeField()
    tipo = models.CharField(max_length=10)
    
    def __str__(self):
        return f"{self.colaborador_id} - {self.documento} - {self.data_hora} - {self.tipo}"
    
    class Meta:
        db_table = 'registro_ponto'
        ordering = ['data_hora']
        verbose_name = 'Registro de Ponto'
        verbose_name_plural = 'Registros de Ponto'