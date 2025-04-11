from django.db import models
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
    enti_empr = models.IntegerField(default=1)
    enti_clie = models.IntegerField(unique=True, primary_key=True) 
    enti_nome = models.CharField(max_length=100, default='')
    enti_tipo_enti = models.CharField(max_length=100, choices=TIPO_ENTIDADES, default='1')
    enti_fant = models.CharField(max_length=100, default='')  
    enti_cpf = models.CharField(max_length=11,  blank=True, null= True)  
    enti_cnpj = models.CharField(max_length=14,  blank=True, null= True)  
    enti_insc_esta = models.CharField(max_length=11, blank=True, null= True)    
    enti_cep = models.CharField(max_length=8) 
    enti_ende = models.CharField(max_length=60)
    enti_nume = models.CharField(max_length=4)  
    enti_cida = models.CharField(max_length=60)
    enti_esta = models.CharField(max_length=2)
    enti_fone = models.CharField(max_length=14, blank=True, null= True)  
    enti_celu = models.CharField(max_length=15, blank=True, null= True)  
    enti_emai = models.CharField(max_length=60, blank=True, null= True)  
    enti_emai_empr = models.CharField(max_length=60,blank=True, null= True)  

    def __str__(self):
        return self.enti_nome

    class Meta:
        db_table = 'entidades'


