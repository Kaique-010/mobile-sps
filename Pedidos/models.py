# models.py
from django.db import models
from Entidades.models import Entidades
from Produtos.models import Produtos

TIPO_FINANCEIRO = [
    ('0', 'À VISTA'),
    ('1', 'A PRAZO'),
    ('2', 'SEM FINANCEIRO'),
]

class PedidoVenda(models.Model):
    pedi_empr = models.IntegerField()
    pedi_fili = models.IntegerField()
    pedi_nume = models.BigAutoField(primary_key=True, unique=True)
    pedi_forn = models.ForeignKey(Entidades, on_delete=models.CASCADE, db_column='pedi_forn', related_name='pedidos_por_clientes')
    pedi_data = models.DateField()
    pedi_tota = models.DecimalField(decimal_places=2, max_digits=15)
    pedi_canc = models.BooleanField(default=False)
    pedi_fina = models.CharField(max_length=100, choices=TIPO_FINANCEIRO, default='0')
    pedi_vend = models.ForeignKey(Entidades, on_delete=models.CASCADE, db_column='pedi_vend', related_name='pedidos_como_vendedor', null=True)  
    pedi_stat = models.CharField(max_length=50, choices=[
        ('Pendente', 'Pendente'),
        ('Processando', 'Processando'),
        ('Enviado', 'Enviado'),
        ('Concluído', 'Concluído'),
        ('Cancelado', 'Cancelado'),
    ], default='Pendente')
    pedi_obse = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'pedidosvenda'
        managed = 'false'

    def __str__(self):
        return f"Pedido {self.pedi_nume} - {self.pedi_forn}"

    
    
class Itenspedidovenda(models.Model):
    iped_empr = models.IntegerField(primary_key=True, db_column='iped_empr')  
    iped_fili = models.IntegerField(unique=True)
    iped_pedi = models.CharField(db_column='iped_pedi', max_length=50)
    iped_item = models.IntegerField()
    iped_prod = models.CharField(max_length=60, db_column='iped_prod') 
    iped_quan = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    iped_unit = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    iped_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    iped_fret = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    iped_desc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    iped_unli = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    iped_forn = models.IntegerField(blank=True, null=True)
    iped_vend = models.IntegerField(blank=True, null=True)
    iped_cust = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    iped_tipo = models.IntegerField(blank=True, null=True)
    iped_desc_item = models.BooleanField(blank=True, null=True)
    iped_perc_desc = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    iped_unme = models.CharField(max_length=6, blank=True, null=True)


    class Meta:
        db_table = 'itenspedidovenda'
        unique_together = (('iped_empr', 'iped_fili', 'iped_pedi', 'iped_item'),)
        managed = 'false'

