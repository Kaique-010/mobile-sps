from django.db import models
from decimal import Decimal


class Situacoes(models.Model):
    situ_codi = models.IntegerField(primary_key=True)
    situ_nome = models.CharField(max_length=60)
    situ_obse = models.TextField(blank=True, null=True)
    situ_nao_list = models.BooleanField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  
    situ_nao_list_cp = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'situacoes'



class Orcamento(models.Model):
    orca_id = models.AutoField(primary_key=True)
    orca_empr = models.IntegerField(verbose_name="Empresa")
    orca_fili = models.IntegerField(verbose_name="Filial", blank=True, null=True)
    orca_desc = models.CharField(max_length=120, verbose_name="Descrição")
    orca_ano = models.IntegerField(verbose_name="Ano")
    orca_tipo = models.CharField(
        max_length=1,
        choices=(
            ("A", "Anual"),
            ("M", "Mensal"),
        ),
        default="M",
        verbose_name="Tipo",
    )
    orca_cena = models.CharField(
        max_length=1,
        choices=(
            ("R", "Realista"),
            ("P", "Pessimista"),
            ("O", "Otimista"),
        ),
        default="R",
        verbose_name="Cenário",
    )
    orca_ativ = models.BooleanField(default=True, verbose_name="Ativo")
    orca_data = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "orcamento_financeiro_cc"


    def __str__(self):
        return f"{self.orca_desc} - {self.orca_ano} - {self.orca_tipo} - {self.orca_cena}"  


class OrcamentoItem(models.Model):
    orci_id = models.AutoField(primary_key=True)
    orci_empr = models.IntegerField(verbose_name="Empresa")
    orci_fili = models.IntegerField(verbose_name="Filial", blank=True, null=True)
    orci_orca = models.IntegerField(verbose_name="ID Orçamento")
    orci_cecu = models.IntegerField(verbose_name="Centro de Custo")
    orci_ano = models.IntegerField(verbose_name="Ano")
    orci_mes = models.IntegerField(verbose_name="Mês")
    orci_valo = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    orci_obse = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "orcamentoitem_financeiro_cc"
        unique_together = (("orci_empr", "orci_fili", "orci_orca", "orci_cecu", "orci_ano", "orci_mes"),)
        ordering = ["orci_id"]
    
    def __str__(self):
        return f"{self.orci_orca} - {self.orci_cecu} - {self.orci_ano} - {self.orci_mes} - {self.orci_valo}"
    