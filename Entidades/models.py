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
    enti_clie = models.BigIntegerField(unique=True, null=True, blank=True)
    enti_nome = models.CharField(max_length=100, default='')
    enti_tipo_enti = models.CharField(max_length=100, choices=TIPO_ENTIDADES, default='1')
    enti_fant = models.CharField(max_length=100, default='')  
    enti_cpf = models.CharField(max_length=11,  blank=True, null=True)  
    enti_cnpj = models.CharField(max_length=14,  blank=True, null=True)  
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
            self.enti_clie = Sequencial.gerar_novo_valor("enti_clie")
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'entidades'


class Sequencial(models.Model):
    nome_sequencial = models.CharField(max_length=100, unique=True)
    ultimo_valor = models.BigIntegerField()

    @staticmethod
    def gerar_novo_valor(nome_sequencial="enti_clie"):
        from .models import Entidades  # importa aqui dentro pra evitar erro de import circular

        with transaction.atomic():
            sequencial, created = Sequencial.objects.get_or_create(nome_sequencial=nome_sequencial)
            
            if created:
                ultimo_valor_enti_clie = Entidades.objects.aggregate(Max('enti_clie'))['enti_clie__max']
                if ultimo_valor_enti_clie is not None:
                    sequencial.ultimo_valor = ultimo_valor_enti_clie
                    logger.info(f'O último valor de enti_clie é: {ultimo_valor_enti_clie}')
                else:
                    sequencial.ultimo_valor = 1
                    logger.info('Não há registros anteriores de enti_clie.')

            sequencial.ultimo_valor += 1
            sequencial.save()

            logger.info(f'Próximo valor gerado para enti_clie será: {sequencial.ultimo_valor}')
            return sequencial.ultimo_valor
