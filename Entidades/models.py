from django.db import models, transaction
from django.db.models import Max
import logging

logger = logging.getLogger(__name__)

class Entidades(models.Model):
    TIPO_ENTIDADES = [
        ('FO', 'FORNECEDOR'),
        ('CL', 'CLIENTE'),
        ('AM', 'AMBOS'),
        ('OU', 'OUTROS'),
        ('VE', 'VENDEDOR'),
        ('FU', 'FUNCIONÁRIOS'),
    ]

    enti_empr = models.IntegerField()
    enti_fili = models.CharField(max_length=100, default='')
    enti_clie = models.BigIntegerField(unique=True, primary_key=True)
    enti_nome = models.CharField(max_length=100, default='')
    enti_tipo_enti = models.CharField(max_length=100, choices=TIPO_ENTIDADES, default='1')
    enti_fant = models.CharField(max_length=100, default='', blank=True, null=True)  
    enti_cpf = models.CharField(max_length=11, blank=True, null=True)  
    enti_cnpj = models.CharField(max_length=14, blank=True, null=True)  
    enti_insc_esta = models.CharField(max_length=11, blank=True, null=True)    
    enti_cep = models.CharField(max_length=8) 
    enti_ende = models.CharField(max_length=60)
    enti_nume = models.CharField(max_length=4)  
    enti_cida = models.CharField(max_length=60)
    enti_esta = models.CharField(max_length=2)
    enti_fone = models.CharField(max_length=14, blank=True, null=True)  
    enti_celu = models.CharField(max_length=15, blank=True, null=True)  
    enti_emai = models.CharField(max_length=60, blank=True, null=True)  

    def __str__(self):
        return self.enti_nome

    def save(self, *args, **kwargs):
        if not self.enti_clie:
            self.enti_clie, self._sequencial_ref = Sequencial.preparar_proximo_valor("enti_clie")
        super().save(*args, **kwargs)

        # Salva o sequencial só se o save da entidade foi bem-sucedido
        if hasattr(self, "_sequencial_ref"):
            self._sequencial_ref.ultimo_valor = self.enti_clie
            self._sequencial_ref.save()
            del self._sequencial_ref

    class Meta:
        db_table = 'entidades'
        managed = 'false'

class Sequencial(models.Model):
    nome_sequencial = models.CharField(max_length=100, unique=True)
    ultimo_valor = models.BigIntegerField(null=True)

    class Meta:
        db_table = 'sequencial'
        managed = 'false'
    
    @staticmethod
    def preparar_proximo_valor(nome_sequencial="enti_clie"):
        from .models import Entidades  # evita import circular

        with transaction.atomic():
            sequencial, _ = Sequencial.objects.select_for_update().get_or_create(
                nome_sequencial=nome_sequencial
            )

            if sequencial.ultimo_valor is None:
                max_valor = Entidades.objects.aggregate(Max('enti_clie'))['enti_clie__max']
                sequencial.ultimo_valor = max_valor or 1
            else:
                sequencial.ultimo_valor += 1

            return sequencial.ultimo_valor, sequencial