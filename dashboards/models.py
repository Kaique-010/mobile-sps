from django.db import models

class OrcamentoAnaliticoView(models.Model):
    plan_redu = models.CharField(max_length=20)
    plan_nome = models.CharField(max_length=255)
    tipo = models.CharField(max_length=10, primary_key=True)
    mes = models.CharField(max_length=20)
    valor_orcado = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    valor_recebido = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    valor_pago = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    saldo = models.DecimalField(max_digits=15, decimal_places=2, null=True)


    class Meta:
        managed = False
        db_table = 'orcamento_2025'



class ExtratoCaixa(models.Model):
    empresa = models.IntegerField(db_column='Empresa')
    filial = models.IntegerField(db_column='Filial')
    pedido = models.IntegerField(db_column='Pedido', primary_key=True)
    cliente = models.IntegerField(db_column='Cliente')
    nome_cliente = models.CharField(max_length=200, db_column='Nome Cliente')
    produto = models.CharField(max_length=100, db_column='Produto')
    descricao = models.CharField(max_length=200, db_column='Descrição')
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, db_column='Quantidade')
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, db_column='Valor Total')
    data = models.DateField(db_column='Data')
    forma_de_recebimento = models.CharField(max_length=50, db_column='Forma de Recebimento')

    class Meta:
        managed = False
        db_table = 'extrato_caixa'



class BalanceteCC(models.Model):
    empr = models.IntegerField()
    fili = models.IntegerField()
    cecu_redu = models.CharField(max_length=10)
    centro_nome = models.CharField(max_length=100, primary_key=True)
    tipo_cc = models.CharField(max_length=1, default='Sem') 
    mes_num = models.CharField(max_length=2)
    mes_nome = models.CharField(max_length=15)
    ano = models.IntegerField()    
    mes_ordem = models.IntegerField()
    valor_recebido = models.DecimalField(max_digits=15, decimal_places=2)
    valor_pago = models.DecimalField(max_digits=15, decimal_places=2)
    resultado = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'balancete_cc'
