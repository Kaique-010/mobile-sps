from django.db import models
from django.utils.translation import gettext_lazy as _
import logging

# Reexportado para compatibilidade com imports existentes (`Entidades.models`)
from core.db_columns import SafeMissingColumnsManager, campo_existe_no_banco

logger = logging.getLogger(__name__)


class Entidades(models.Model):
    TIPO_ENTIDADES = [
        ('FO', 'FORNECEDOR'),
        ('CL', 'CLIENTE'),
        ('AM', 'AMBOS'),
        ('OU', 'OUTROS'),
        ('VE', 'VENDEDOR'),
        ('FU', 'FUNCIONÁRIOS'),
        ('AR', 'ARQUITETOS'),
    ]
    
        
    CLASSIFICACAO_TRIBUTACAO = (
        ('000', _('Consumidor Final')),
        ('001', _('Consumidor Final comercio')),
        ('002', _('Consumidor Final Industria')),
        ('003', _('Revenda Comercio')),
        ('004', _('Revenda Industria')),
        ('005', _('Transportes')),
        ('006', _('Orgão Público')),
        ('007', _('Sistemas Financeiros')),
        ('008', _('Entidades Filantrópicas')),
        ('009', _('Produtoe Rural')),
        ('010', _('Orgao Público Federal')),
        ('011', _('Outros')),
    )

    enti_empr = models.IntegerField()
    enti_clie = models.BigIntegerField(unique=True, primary_key=True)
    enti_nome = models.CharField(max_length=100, default='')
    enti_tipo_enti = models.CharField(max_length=100, choices=TIPO_ENTIDADES, default='FO')
    enti_espe_enti = models.CharField(
        max_length=3,
        choices=CLASSIFICACAO_TRIBUTACAO,
        blank=True,
        null=True,
        default='000',
        verbose_name=_('Tipo de Tributação'),
    )
    enti_fant = models.CharField(max_length=100, default='', blank=True, null=True)  
    enti_cpf = models.CharField(max_length=11, blank=True, null=True)  
    enti_cnpj = models.CharField(max_length=14, blank=True, null=True)  
    enti_insc_esta = models.CharField(max_length=14, blank=True, null=True)    
    enti_cep = models.CharField(max_length=8) 
    enti_ende = models.CharField(max_length=60)
    enti_nume = models.CharField(max_length=10)  
    enti_cida = models.CharField(max_length=60)
    enti_esta = models.CharField(max_length=2)
    enti_pais = models.CharField(max_length=60, default='1058')
    enti_codi_pais = models.CharField(max_length=6, default='1058')
    enti_codi_cida = models.CharField(max_length=7, default='0000000')
    enti_bair = models.CharField(max_length=60)
    enti_comp = models.CharField(max_length=60, blank=True, null=True)
    enti_fone = models.CharField(max_length=14, blank=True, null=True)  
    enti_celu = models.CharField(max_length=15, blank=True, null=True)  
    enti_emai = models.CharField(max_length=100, blank=True, null=True)  
    
    #usuarios do Login de cliente 
    enti_mobi_usua = models.CharField(max_length=100, blank=True, null=True)  
    enti_mobi_senh = models.CharField(max_length=100, blank=True, null=True)
    enti_mobi_prec = models.BooleanField(default=True) # Permissão Preço Usuário 1
    enti_mobi_foto = models.BooleanField(default=True) # Permissão Foto Usuário 1
    
    enti_usua_mobi = models.CharField(max_length=100, blank=True, null=True)
    enti_senh_mobi = models.CharField(max_length=100, blank=True, null=True)
    enti_usua_prec = models.BooleanField(default=True) # Permissão Preço Usuário 2
    enti_usua_foto = models.BooleanField(default=True) # Permissão Foto Usuário 2
    
    enti_vend = models.IntegerField(blank=True, null=True, verbose_name='Vendedor responsável')  
    enti_arqu = models.IntegerField(blank=True, null=True, verbose_name='Arquiteto responsável')
    enti_situ = models.CharField(max_length=100,choices=[('0', 'INATIVO'), ('1', 'ATIVO')], default='1')

    # Campos adicionais para banco/caixa

    enti_banc = models.CharField(max_length=100, blank=True, null=True)
    enti_agen = models.CharField(max_length=100, blank=True, null=True)
    enti_tien = models.CharField(max_length=100, blank=True, null=True, choices=[('B', 'BANCO'), ('C', 'CAIXA'), ('E','Entidade'), ('D','Outros')], default='E')
    enti_diag = models.CharField(max_length=100, blank=True, null=True)
    enti_coco = models.CharField(max_length=100, blank=True, null=True)
    enti_dico = models.CharField(max_length=100, blank=True, null=True)
    enti_dana = models.DateField(blank=True, null=True)
    
    
    

    objects = SafeMissingColumnsManager()


    def __str__(self):
        return self.enti_nome
    class Meta:
        db_table = 'entidades'
