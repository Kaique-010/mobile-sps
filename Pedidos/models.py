# models.py
from django.db import models

FORMAS_RECEBIMENTO = [
   ('00', 'DUPLICATA'),
   ('01', 'CHEQUE'),
   ('02', 'PROMISSÓRIA'),
   ('03', 'RECIBO'),
   ('50', 'CHEQUE PRÉ'),
   ('51', 'CARTÃO DE CRÉDITO'),
   ('52', 'CARTÃO DE DÉBITO'),
   ('53', 'BOLETO BANCÁRIO'),
   ('54', 'DINHEIRO'),
   ('55', 'DEPÓSITO EM CONTA'),
   ('56', 'VENDA À VISTA'),
   ('60', 'PIX'),
]

TIPO_FINANCEIRO = [
    ('0', 'À VISTA'),
    ('1', 'A PRAZO'),
    ('2', 'SEM FINANCEIRO'),
    ('3', 'NA EMISSÃO'),
]

STATUS_PEDIDO = [
    ('0', 'Pendente'),
    ('1', 'Processando'),
    ('2', 'Enviado'),
    ('3', 'Concluído'),
    ('4', 'Cancelado'),
]

TIPO_OPER_CHOICES = [
        ("VENDA", "Venda"),
        ("DEVOLUCAO_VENDA", "Devolução de Venda"),
        ("REMESSA", "Remessa"),
        ("TRANSFERENCIA", "Transferência"),
        ("BONIFICACAO", "Bonificação"),
        ("EXPORTACAO", "Exportação"),
    ]

    

class PedidoVenda(models.Model):
    pedi_empr = models.IntegerField()
    pedi_fili = models.IntegerField()
    pedi_nume = models.IntegerField(primary_key=True)
    pedi_forn = models.CharField(db_column='pedi_forn',max_length=60)
    pedi_data = models.DateField()
    pedi_topr = models.DecimalField(db_column='pedi_topr', max_digits=15, decimal_places=2, blank=True, null=True)
    pedi_tota = models.DecimalField(decimal_places=2, max_digits=15)
    pedi_canc = models.BooleanField(default=False)
    pedi_fina = models.CharField(max_length=100, choices=TIPO_FINANCEIRO, default='0')
    pedi_vend = models.CharField( db_column='pedi_vend', max_length=15, default=0)  
    pedi_stat = models.CharField(max_length=50, choices=STATUS_PEDIDO, default='0')
    pedi_form_rece = models.CharField(max_length=100, choices=FORMAS_RECEBIMENTO, default='54')
    pedi_obse = models.TextField(blank=True, null=True)
    pedi_desc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    pedi_liqu = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    pedi_tipo_oper = models.CharField(max_length=30, choices=TIPO_OPER_CHOICES, default='VENDA') 


    class Meta:
        db_table = 'pedidosvenda'
        managed = 'false'
        unique_together = ('pedi_empr', 'pedi_fili', 'pedi_nume')

    def __str__(self):
        return f"Pedido {self.pedi_nume} - {self.pedi_forn}"
    
    def get_uf_origem(self, banco=None):
        try:
            from Licencas.models import Filiais
            qs = Filiais.objects
            if banco:
                qs = qs.using(banco)
            f = qs.filter(empr_empr=int(self.pedi_empr), empr_codi=int(self.pedi_fili)).first()
            return (getattr(f, 'empr_esta', '') or '') if f else ''
        except Exception:
            return ''
    
    @property
    def cliente(self):
        try:
            from Entidades.models import Entidades
            return Entidades.objects.filter(enti_clie=self.pedi_forn, enti_empr=self.pedi_empr).first()
        except Exception:
            return None
    
    @property
    def itens(self):
        """
        Retorna um queryset dos itens relacionados a este pedido
        """
        return Itenspedidovenda.objects.filter(
            iped_empr=self.pedi_empr,
            iped_fili=self.pedi_fili,
            iped_pedi=str(self.pedi_nume)
        )

    
    
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
    iped_lote_vend = models.IntegerField(blank=True, null=True)


    class Meta:
        db_table = 'itenspedidovenda'
        unique_together = (('iped_empr', 'iped_fili', 'iped_pedi', 'iped_item'),)
        managed = 'false'

    @property
    def pedido(self):
        try:
            return PedidoVenda.objects.filter(pedi_empr=self.iped_empr, pedi_fili=self.iped_fili, pedi_nume=int(self.iped_pedi)).first()
        except Exception:
            return None

    @property
    def produto(self):
        try:
            from Produtos.models import Produtos
            return Produtos.objects.filter(prod_codi=self.iped_prod, prod_empr=str(self.iped_empr)).first()
        except Exception:
            return None




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





class Parcelaspedidovenda(models.Model):
    parc_empr = models.IntegerField()
    parc_fili = models.IntegerField()
    parc_pedi = models.IntegerField()
    parc_parc = models.IntegerField(primary_key=True)
    parc_forn = models.IntegerField()
    parc_emis = models.DateField(blank=True, null=True)
    parc_venc = models.DateField(blank=True, null=True)
    parc_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    parc_port = models.IntegerField(blank=True, null=True)
    parc_situ = models.IntegerField(blank=True, null=True)
    parc_form = models.CharField(max_length=2, blank=True, null=True)
    parc_avis = models.BooleanField(blank=True, null=True)
    parc_vend = models.IntegerField(blank=True, null=True)
    parc_cecu = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'parcelaspedidovenda'
        unique_together = (('parc_empr', 'parc_fili', 'parc_pedi', 'parc_parc', 'parc_forn'),)

