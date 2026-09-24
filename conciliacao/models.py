
from django.db import models


class ConciliacaoBancaria(models.Model):
    nume = models.IntegerField(
        db_column="conc_nume",
        primary_key=True,
    )

    empresa = models.IntegerField(
        db_column="conc_empr",
    )

    filial = models.IntegerField(
        db_column="conc_fili",
    )

    codigo_banco = models.IntegerField(
        db_column="conc_codi_banc",
    )

    url_ofx = models.CharField(
        max_length=255,
        db_column="conc_url_ofx",
        null=True,
        blank=True,
    )

    arquivo_ofx = models.TextField(
        db_column="conc_arqu_ofx",
        null=True,
        blank=True,
    )

    data = models.DateField(
        db_column="conc_data",
        null=True,
        blank=True,
    )

    class Meta:
        managed = False
        db_table = "conciliacaobancaria"


class ItemBanco(models.Model):
    id = models.AutoField(primary_key=True)

    nume = models.IntegerField(
        db_column="conc_banc_nume",
    )

    empresa = models.IntegerField(
        db_column="conc_banc_empr",
    )

    filial = models.IntegerField(
        db_column="conc_banc_fili",
    )

    documento = models.CharField(
        max_length=255,
        db_column="conc_banc_docu",
        null=True,
        blank=True,
    )

    data_operacao = models.DateField(
        db_column="conc_banc_data_op",
        null=True,
        blank=True,
    )

    tipo = models.CharField(
        max_length=1,
        db_column="conc_banc_tipo",
        null=True,
        blank=True,
    )

    valor = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        db_column="conc_banc_valo",
        null=True,
        blank=True,
    )

    historico = models.CharField(
        max_length=255,
        db_column="conc_banc_hist",
        null=True,
        blank=True,
    )

    existe = models.BooleanField(
        db_column="conc_banc_exis",
        null=True,
        default=False,
    )

    selecionado = models.BooleanField(
        db_column="conc_banc_sele",
        null=True,
        default=False,
    )

    linha = models.IntegerField(
        db_column="conc_banc_linh",
    )

    class Meta:
        managed = False
        db_table = "conciliacao_itens_banco"


class ItemExtrato(models.Model):
    id = models.AutoField(primary_key=True)

    nume = models.IntegerField(
        db_column="conc_extr_nume",
    )

    empresa = models.IntegerField(
        db_column="conc_extr_empr",
    )

    filial = models.IntegerField(
        db_column="conc_extr_fili",
    )

    documento = models.CharField(
        max_length=255,
        db_column="conc_extr_docu",
        null=True,
        blank=True,
    )

    data_operacao = models.DateField(
        db_column="conc_extr_data_op",
        null=True,
        blank=True,
    )

    tipo = models.CharField(
        max_length=1,
        db_column="conc_extr_tipo",
        null=True,
        blank=True,
    )

    valor = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        db_column="conc_extr_valo",
        null=True,
        blank=True,
    )

    historico = models.CharField(
        max_length=255,
        db_column="conc_extr_hist",
        null=True,
        blank=True,
    )

    existe = models.BooleanField(
        db_column="conc_extr_exis",
        null=True,
        default=False,
    )

    selecionado = models.BooleanField(
        db_column="conc_extr_sele",
        null=True,
        default=False,
    )

    linha = models.IntegerField(
        db_column="conc_extr_linh",
    )

    class Meta:
        managed = False
        db_table = "conciliacao_itens_extrato"


class ConciliacaoHist(models.Model):
    id = models.AutoField(primary_key=True)

    nume = models.IntegerField(
        db_column="conc_hist_nume"
    )
    empresa = models.IntegerField(
        db_column="conc_hist_empr"
    )
    filial = models.IntegerField(
        db_column="conc_hist_fili"
    )

    item_extrato = models.IntegerField(
        db_column="conc_hist_item_extrato"
    )
    origem = models.CharField(
        max_length=10,
        db_column="conc_hist_origem"
    )

    titulo = models.CharField(
        max_length=13,
        db_column="conc_hist_titu",
        null=True,
        blank=True,
    )
    entidade = models.IntegerField(
        db_column="conc_hist_enti",
        null=True,
        blank=True,
    )
    serie = models.CharField(
        max_length=5,
        db_column="conc_hist_seri",
        null=True,
        blank=True,
    )
    parcela = models.CharField(
        max_length=4,
        db_column="conc_hist_parc",
        null=True,
        blank=True,
    )

    banco = models.IntegerField(
        db_column="conc_hist_banc",
        null=True,
        blank=True,
    )
    controle_bancario = models.IntegerField(
        db_column="conc_hist_ctrl_banc",
        null=True,
        blank=True,
    )

    valor = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        db_column="conc_hist_valor",
    )

    data = models.DateTimeField(
        db_column="conc_hist_data",
        auto_now_add=True,
    )
    
    baixa_pagar_sequ = models.IntegerField(
    db_column="conc_hist_baixa_pagar_sequ",
    null=True,
    blank=True,
    )

    baixa_receber_sequ = models.IntegerField(
        db_column="conc_hist_baixa_receber_sequ",
        null=True,
        blank=True,
    )

    class Meta:
        managed = False
        db_table = "conciliacao_hist"
        verbose_name = "Histórico de Conciliação"
        verbose_name_plural = "Históricos de Conciliação"

    def __str__(self):
        return "{} - {} - {}".format(
            self.nume,
            self.item_extrato,
            self.origem,
        )