from django.db import models

# Create your models here.

class RegraComissao(models.Model):
    regc_id = models.AutoField(primary_key=True)
    regc_empr = models.IntegerField(verbose_name="Empresa")
    regc_fili = models.IntegerField(verbose_name="Filial")
    regc_bene = models.IntegerField(verbose_name="Vendedor/Beneficiário")  # entidade
    regc_perc = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Percentual Comissão")
    regc_ativ = models.BooleanField(default=True, verbose_name="Ativo")
    regc_data_ini = models.DateField(blank=True, null=True, verbose_name="Data Inicial")
    regc_data_fim = models.DateField(blank=True, null=True, verbose_name="Data Final")
    regc_cecu = models.IntegerField(default=0, verbose_name="Cento de Custo", blank=True, null=True)

    class Meta:
        db_table = "regras_comissoes_web"
        ordering = ["regc_id"]
        verbose_name = "Regra Comissão"
        verbose_name_plural = "Regras Comissões"


class LancamentoComissao(models.Model):
    STATUS_ABERTO = 1
    STATUS_PAGO = 2
    STATUS_PARCIAL = 3
    STATUS_CANCELADO = 4
    STATUS_ESTORNADO = 5

    STATUS_CHOICES = (
        (STATUS_ABERTO, "Em aberto"),
        (STATUS_PAGO, "Pago"),
        (STATUS_PARCIAL, "Parcial"),
        (STATUS_CANCELADO, "Cancelado"),
        (STATUS_ESTORNADO, "Estornado"),
    )
    
    TIPO_ORIGEM_CHOICES = (
        ("pedido", "Pedido"),
        ("nota", "Nota"),
        ("titulo", "Título"),
    )

    lcom_id = models.AutoField(primary_key=True)
    lcom_empr = models.IntegerField(verbose_name="Empresa")
    lcom_fili = models.IntegerField(verbose_name="Filial")
    lcom_regra = models.ForeignKey(RegraComissao, on_delete=models.PROTECT, verbose_name="Regra Comissão")
    lcom_bene = models.IntegerField(verbose_name="Vendedor/Beneficiário")  # snapshot do beneficiário
    lcom_data = models.DateField(verbose_name="Data")
    lcom_tipo_origem = models.CharField(max_length=20, blank=True, null=True, choices=TIPO_ORIGEM_CHOICES, verbose_name="Tipo Origem")  # pedido, nota, titulo
    lcom_docu = models.CharField(max_length=20, verbose_name="Documento")
    lcom_base = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Base Comissão")
    lcom_perc = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Percentual Comissão")
    lcom_valo = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Valor Comissão")
    lcom_stat = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_ABERTO)
    lcom_obse = models.TextField(blank=True, null=True, verbose_name="Observação")
    lcom_cecu = models.IntegerField(default=0, verbose_name="Cento de Custo", blank=True, null=True)

    class Meta:
        verbose_name = "Lançamento Comissão"
        verbose_name_plural = "Lancamentos Comissões"
        db_table = "lancamentos_comissoes_web"
        ordering = ["lcom_id"]
        unique_together = [("lcom_empr", "lcom_fili", "lcom_bene", "lcom_tipo_origem", "lcom_docu")]



class PagamentoComissao(models.Model):
    pagc_id = models.AutoField(primary_key=True)
    pagc_empr = models.IntegerField(verbose_name="Empresa")
    pagc_fili = models.IntegerField(verbose_name="Filial")
    pagc_data = models.DateField(verbose_name="Data")
    pagc_bene = models.IntegerField(verbose_name="Vendedor/Beneficiário")
    pagc_valo = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Valor Pagamento")
    pagc_obse = models.TextField(blank=True, null=True, verbose_name="Observação")
    pagc_cecu = models.IntegerField(default=0, verbose_name="Cento de Custo", blank=True, null=True)

    
    class Meta:
        db_table = "pagamentos_comissoes_web"
        ordering = ["pagc_id"]
        verbose_name = "Pagamento Comissão"
        verbose_name_plural = "Pagamentos Comissões"


class PagamentoComissaoItem(models.Model):
    pgci_id = models.AutoField(primary_key=True)
    pgci_paga = models.ForeignKey(PagamentoComissao, on_delete=models.CASCADE, related_name="itens")
    pgci_lanc = models.ForeignKey(LancamentoComissao, on_delete=models.PROTECT, verbose_name="Lançamento Comissão")
    pgci_valo = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Valor Pagamento")
    pgci_obse = models.TextField(blank=True, null=True, verbose_name="Observação")
    pgci_cecu = models.IntegerField(default=0, verbose_name="Cento de Custo", blank=True, null=True)

    class Meta:
        db_table = "pagamentos_comissoes_itens_web"
        ordering = ["pgci_id"]
        verbose_name = "Item Pagamento Comissão"
        verbose_name_plural = "Itens Pagamentos Comissões"