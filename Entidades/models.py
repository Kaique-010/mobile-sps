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
    enti_clie = models.BigIntegerField(unique=True, primary_key=True)
    enti_nome = models.CharField(max_length=100, default='')
    enti_tipo_enti = models.CharField(max_length=100, choices=TIPO_ENTIDADES, default='FO')
    enti_fant = models.CharField(max_length=100, default='', blank=True, null=True)  
    enti_cpf = models.CharField(max_length=11, blank=True, null=True)  
    enti_cnpj = models.CharField(max_length=14, blank=True, null=True)  
    enti_insc_esta = models.CharField(max_length=11, blank=True, null=True)    
    enti_cep = models.CharField(max_length=8) 
    enti_ende = models.CharField(max_length=60)
    enti_nume = models.CharField(max_length=4)  
    enti_cida = models.CharField(max_length=60)
    enti_esta = models.CharField(max_length=2)
    enti_pais = models.CharField(max_length=60, default='1058')
    enti_codi_pais = models.CharField(max_length=6, default='1058')
    enti_codi_cida = models.CharField(max_length=7, default='0000000')
    enti_bair = models.CharField(max_length=60)
    enti_comp = models.CharField(max_length=60, blank=True, null=True)
    enti_fone = models.CharField(max_length=14, blank=True, null=True)  
    enti_celu = models.CharField(max_length=15, blank=True, null=True)  
    enti_emai = models.CharField(max_length=60, blank=True, null=True)  
    enti_mobi_usua = models.CharField(max_length=100, blank=True, null=True)  
    enti_mobi_senh = models.CharField(max_length=100, blank=True, null=True)  
    enti_vend = models.IntegerField(blank=True, null=True)  

    # Campos adicionais para banco/caixa

    enti_banc = models.CharField(max_length=100, blank=True, null=True)
    enti_agen = models.CharField(max_length=100, blank=True, null=True)
    enti_tien = models.CharField(max_length=100, blank=True, null=True, choices=[('B', 'BANCO'), ('C', 'CAIXA'), ('E','Entidade'), ('D','Outros')], default='E')
    enti_diag = models.CharField(max_length=100, blank=True, null=True)
    enti_coco = models.CharField(max_length=100, blank=True, null=True)
    enti_dico = models.CharField(max_length=100, blank=True, null=True)
    
    
    


    def __str__(self):
        return self.enti_nome
    class Meta:
        db_table = 'entidades'
        managed = 'false'

