from django.db import models


class TabelaprecosPromocional(models.Model):
    tabe_id = models.BigAutoField(primary_key=True, db_column='tabe_id')
    tabe_empr = models.IntegerField()
    tabe_fili = models.IntegerField(db_column='tabe_fili', verbose_name="Filial")
    tabe_prod = models.CharField( max_length=60, db_column='tabe_prod', verbose_name="Produto")
    tabe_prco = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="Preço de Compra")
    tabe_desp = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name="Despesas")
    tabe_cust = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="Custos")
    tabe_marg = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name="Margem")
    tabe_cuge = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="Custo Gerencial")
    tabe_avis = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="Preço à Vista")
    tabe_praz = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name="Prazo")
    tabe_apra = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="Preço a Prazo")
    tabe_hist = models.TextField(blank=True, null=True, verbose_name="Histórico")
    tabe_perc_reaj = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="Percentual de Reajuste")



    class Meta:
        db_table = 'tabelaprecos_promocional'
        unique_together = (('tabe_empr', 'tabe_fili', 'tabe_prod'),)
        managed = False
        verbose_name = 'Tabela de Preço'
        verbose_name_plural = 'Tabelas de Preços'

    def __str__(self):
        return f"{self.tabe_prod} - R$ {self.tabe_prco or 0:.2f}"

    @property
    def preco_formatado(self):
        return f"R$ {self.tabe_prco or 0:.2f}"



class TabelaprecosPromocionalhist(models.Model):
    tabe_id = models.AutoField(primary_key=True)
    tabe_empr = models.IntegerField()
    tabe_fili = models.IntegerField()
    tabe_prod = models.CharField(max_length=20)
    tabe_data_hora = models.DateTimeField()
    tabe_perc_reaj = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_avis_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_avis_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_apra_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_apra_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_hist = models.TextField(blank=True, null=True)
    tabe_prco_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_prco_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_desp_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_desp_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_cust_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_cust_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_cuge_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_cuge_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_marg_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_marg_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_praz_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_praz_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = 'tabelaprecosPromocionalhist'
        managed = False
