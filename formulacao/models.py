from django.db import models
from Produtos.models import Produtos



class FormulaProduto(models.Model):
    form_empr = models.IntegerField()
    form_fili = models.IntegerField()
    form_prod = models.ForeignKey(Produtos, models.DO_NOTHING, db_column='form_prod', db_constraint=False)
    form_vers = models.IntegerField()
    form_ativ = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'formulaproduto'
        unique_together = (('form_empr', 'form_fili', 'form_prod', 'form_vers'),)
    
    def __str__(self):
        return f"{self.form_empr} {self.form_fili} {self.form_prod} {self.form_vers}"

class FormulaItem(models.Model):
    form_empr = models.IntegerField()
    form_fili = models.IntegerField()
    form_form = models.ForeignKey(FormulaProduto, models.DO_NOTHING, db_column='form_form', db_constraint=False)
    form_insu = models.ForeignKey(Produtos, models.DO_NOTHING, db_column='form_insu', db_constraint=False)

    form_vers = models.IntegerField()
    form_item = models.IntegerField()
    form_qtde = models.DecimalField(max_digits=15, decimal_places=4)
    form_perd_perc = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    form_baixa_estoque = models.BooleanField(default=True)

    
    class Meta:
        managed = True
        db_table = 'formulaitem'
        unique_together = (('form_empr', 'form_fili', 'form_insu', 'form_vers', 'form_item'),)
        
    def __str__(self):
        return f"{self.form_empr} {self.form_fili} {self.form_insu} {self.form_vers} {self.form_item}"


class FormulaSaida(models.Model):
    said_empr = models.IntegerField()
    said_fili = models.IntegerField()
    said_form = models.ForeignKey(FormulaProduto, models.DO_NOTHING, db_column='said_form', db_constraint=False)

    said_prod = models.ForeignKey(Produtos, models.DO_NOTHING, db_column='said_prod', db_constraint=False)

    said_quan = models.DecimalField(max_digits=15, decimal_places=4)
    said_perc_cust = models.DecimalField(max_digits=5, decimal_places=2)

    said_principal = models.BooleanField(default=False)

    class Meta:
        managed = True
        db_table = 'formulasaida'
    
    def __str__(self):
        return f"{self.said_empr} {self.said_fili} {self.said_form} {self.said_prod} {self.said_quan} {self.said_perc_cust} {self.said_principal}"

class OrdemProducao(models.Model):
    op_empr = models.IntegerField()
    op_fili = models.IntegerField()
    op_nume = models.IntegerField(primary_key=True)

    op_data = models.DateField()
    op_data_hora = models.DateTimeField(null=True, blank=True)

    op_prod = models.ForeignKey(Produtos, models.DO_NOTHING, db_column='op_prod', db_constraint=False)  # legado
    op_vers = models.IntegerField()

    op_quan = models.DecimalField(max_digits=15, decimal_places=4)
    op_status = models.CharField(max_length=1)

    op_lote = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'opformulacao'
        unique_together = (('op_empr', 'op_fili', 'op_nume'),)
    
    def __str__(self):
        return f"{self.op_empr} {self.op_fili} {self.op_nume}"
