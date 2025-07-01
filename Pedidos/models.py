# models.py
from django.db import models


TIPO_FINANCEIRO = [
    ('0', 'À VISTA'),
    ('1', 'A PRAZO'),
    ('2', 'SEM FINANCEIRO'),
]

class PedidoVenda(models.Model):
    pedi_empr = models.IntegerField()
    pedi_fili = models.IntegerField()
    pedi_nume = models.IntegerField(primary_key=True, unique=True)
    pedi_forn = models.CharField(db_column='pedi_forn',max_length=60)
    pedi_data = models.DateField()
    pedi_tota = models.DecimalField(decimal_places=2, max_digits=15)
    pedi_canc = models.BooleanField(default=False)
    pedi_fina = models.CharField(max_length=100, choices=TIPO_FINANCEIRO, default='0')
    pedi_vend = models.CharField( db_column='pedi_vend', max_length=15, default=0)  
    pedi_stat = models.CharField(max_length=50, choices=[
        (0, 'Pendente'),
        (1, 'Processando'),
        (2, 'Enviado'),
        (3, 'Concluído'),
        (4, 'Cancelado'),
    ], default=0)
    pedi_obse = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'pedidosvenda'
        managed = 'false'
        unique_together = ('pedi_empr', 'pedi_fili', 'pedi_nume')

    def __str__(self):
        return f"Pedido {self.pedi_nume} - {self.pedi_forn}"

    
    
class Itenspedidovenda(models.Model):
    iped_empr = models.IntegerField(unique=True)  
    iped_fili = models.IntegerField(unique=True)
    iped_pedi = models.CharField(db_column='iped_pedi', max_length=50, unique=True, primary_key=True)
    iped_item = models.IntegerField()
    iped_prod = models.CharField(max_length=60, db_column='iped_prod') 
    iped_quan = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    iped_unit = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    iped_suto = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
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
    iped_data = models.DateField(auto_now=True)


    class Meta:
        db_table = 'itenspedidovenda'
        unique_together = (('iped_empr', 'iped_fili', 'iped_pedi', 'iped_item'),)
        managed = 'false'




class PedidosGeral(models.Model):
    empresa = models.IntegerField()
    filial = models.IntegerField()
    numero_pedido = models.IntegerField(primary_key=True)
    codigo_cliente = models.IntegerField()
    nome_cliente = models.CharField(max_length=100)
    data_pedido = models.DateField()
    quantidade_total = models.DecimalField(max_digits=10, decimal_places=2)
    itens_do_pedido = models.TextField()
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    tipo_financeiro = models.CharField(max_length=50)
    nome_vendedor = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'pedidos_geral'