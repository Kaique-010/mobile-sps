from django.db import models

# Create your models here.
class EnviarCobranca(models.Model):
    empresa = models.IntegerField()
    filial = models.IntegerField()
    cliente_id = models.IntegerField()
    cliente_nome = models.CharField(max_length=100)
    cliente_celular = models.CharField(max_length=20, blank=True, null=True)
    cliente_telefone = models.CharField(max_length=20, blank=True, null=True)
    numero_titulo = models.CharField(max_length=13, primary_key=True)
    serie = models.CharField(max_length=5)
    parcela = models.CharField(max_length=3)
    vencimento = models.DateField()
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    forma_recebimento_codigo = models.CharField(max_length=2)
    forma_recebimento_nome = models.CharField(max_length=50)
    linha_digitavel = models.CharField(max_length=255, blank=True, null=True)
    url_boleto = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'enviarcobranca'
