# notas_fiscais/models.py

from django.db import models
from django.utils import timezone
from Entidades.models import Entidades
from Licencas.models import Filiais
from Produtos.models import Produtos



# ============================================================
# CHOICES / CONSTANTES
# ============================================================

MODELO_CHOICES = [
    ("55", "NF-e"),
    ("65", "NFC-e"),
]

TIPO_OPERACAO = [
    (0, "Entrada"),
    (1, "Saída"),
]

FINALIDADE_CHOICES = [
    (1, "Normal"),
    (2, "Complementar"),
    (3, "Ajuste"),
    (4, "Devolução"),
]

AMBIENTE_CHOICES = [
    (1, "Produção"),
    (2, "Homologação"),
]

STATUS_CHOICES = [
    (0, "Rascunho"),
    (100, "Autorizada"),
    (101, "Cancelada"),
    (102, "Inutilizada"),
    (301, "Dendegada(Irregularidade Emitente)"),
    (302, "Dendegada(Irregularidade Destinatário)"),
]

MODALIDADE_FRETE = [
    (0, "Emitente"),
    (1, "Destinatário"),
    (2, "Terceiros"),
    (9, "Sem Frete"),
]


# ============================================================
# MODELS
# ============================================================

class Nota(models.Model):
    empresa = models.IntegerField()
    filial = models.IntegerField()

    modelo = models.CharField(max_length=2, choices=MODELO_CHOICES, default="55")
    serie = models.CharField(max_length=3)
    numero = models.IntegerField()

    data_emissao = models.DateField(default=timezone.now)
    data_saida = models.DateField(blank=True, null=True)

    tipo_operacao = models.IntegerField(choices=TIPO_OPERACAO)
    finalidade = models.IntegerField(choices=FINALIDADE_CHOICES, default=1)
    ambiente = models.IntegerField(choices=AMBIENTE_CHOICES, default=2)

    # PARTICIPANTES REAIS
    emitente = models.ForeignKey(Filiais, on_delete=models.PROTECT, db_constraint=False)
    destinatario = models.ForeignKey(Entidades, on_delete=models.PROTECT, db_constraint=False)

    status = models.IntegerField(choices=STATUS_CHOICES, default=0)
    chave_acesso = models.CharField(max_length=50, blank=True, null=True)
    protocolo_autorizacao = models.CharField(max_length=60, blank=True, null=True)
    motivo_status = models.TextField(blank=True, null=True, help_text="Motivo do status retornado pela SEFAZ")

    xml_assinado = models.TextField(blank=True, null=True)
    xml_autorizado = models.TextField(blank=True, null=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nf_nota"
        unique_together = ("empresa", "filial", "modelo", "serie", "numero")



# ------------------------------------------------------------

class NotaItem(models.Model):
    nota = models.ForeignKey(Nota, related_name="itens", on_delete=models.CASCADE)
    produto = models.ForeignKey(Produtos, on_delete=models.PROTECT, db_constraint=False)

    quantidade = models.DecimalField(max_digits=15, decimal_places=4)
    unitario = models.DecimalField(max_digits=15, decimal_places=4)
    desconto = models.DecimalField(max_digits=15, decimal_places=4, default=0)

    cfop = models.CharField(max_length=4)
    ncm = models.CharField(max_length=8)
    cest = models.CharField(max_length=7, blank=True, null=True)

    cst_icms = models.CharField(max_length=3)
    cst_ipi = models.CharField(max_length=3, blank=True, null=True)
    cst_pis = models.CharField(max_length=2)
    cst_cofins = models.CharField(max_length=2)
    cst_ibs = models.CharField(max_length=3, blank=True, null=True)
    cst_cbs = models.CharField(max_length=3, blank=True, null=True)

    fonte_tributacao = models.CharField(max_length=20, null=True, blank=True)

    total_item = models.DecimalField(max_digits=15, decimal_places=2)

    valor_frete = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True)
    valor_seguro = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True)
    valor_outras_despesas = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True)

    class Meta:
        db_table = "nf_nota_item"
        verbose_name = "Item Nota Fiscal (Domínio)"
        verbose_name_plural = "Itens Nota Fiscal (Domínio)"
        indexes = [
            models.Index(fields=["nota"]),
            models.Index(fields=["produto"]),
        ]

    def __str__(self):
        # Usamos self.produto_id para evitar query automática no ForeignKey
        # que pode falhar se o produto não for único (MultipleObjectsReturned)
        return f"{self.produto_id} – {self.quantidade} x {self.unitario}"

    @property
    def produto_display(self):
        """Retorna nome do produto filtrando por empresa para evitar erro de múltiplos objetos"""
        try:
            from Produtos.models import Produtos
            # Tenta pegar empresa da nota (se já carregada) ou via query simples
            if hasattr(self, 'nota') and self.nota:
                empresa = self.nota.empresa
            else:
                # Fallback improvável, mas seguro
                return self.produto_id
            
            p = Produtos.objects.filter(prod_codi=self.produto_id, prod_empr=empresa).first()
            if p:
                return f"{p.prod_nome}"
            return self.produto_id
        except Exception:
            return self.produto_id

    @property
    def total(self):
        if self.total_item is not None:
            return self.total_item
        quantidade = self.quantidade or 0
        unitario = self.unitario or 0
        desconto = self.desconto or 0
        return quantidade * unitario - desconto
# ------------------------------------------------------------

class NotaItemImposto(models.Model):
    item = models.OneToOneField(NotaItem, related_name="impostos", on_delete=models.CASCADE)

    # — ICMS
    icms_base = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    icms_valor = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    icms_aliquota = models.DecimalField(max_digits=5, decimal_places=2, null=True)

    icms_st_base = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    icms_st_valor = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    icms_st_aliquota = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    icms_mva_st = models.DecimalField(max_digits=5, decimal_places=2, null=True)

    # — IPI / PIS / COFINS
    ipi_base = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    ipi_aliquota = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    ipi_valor = models.DecimalField(max_digits=15, decimal_places=2, null=True)

    pis_base = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    pis_aliquota = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    pis_valor = models.DecimalField(max_digits=15, decimal_places=2, null=True)

    cofins_base = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    cofins_aliquota = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    cofins_valor = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    
    # — FCP
    fcp_valor = models.DecimalField(max_digits=15, decimal_places=2, null=True)

    # — IBS / CBS (Reforma Tributária)
    ibs_base = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    ibs_aliquota = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    ibs_valor = models.DecimalField(max_digits=15, decimal_places=2, null=True)

    cbs_base = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    cbs_aliquota = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    cbs_valor = models.DecimalField(max_digits=15, decimal_places=2, null=True)

    class Meta:
        db_table = "nf_item_imposto"
        verbose_name = "Impostos do Item (Domínio)"
        verbose_name_plural = "Impostos dos Itens (Domínio)"
        indexes = [
            models.Index(fields=["item"])
        ]


# ------------------------------------------------------------

class Transporte(models.Model):
    nota = models.OneToOneField(Nota, related_name="transporte", on_delete=models.CASCADE)

    modalidade_frete = models.IntegerField(choices=MODALIDADE_FRETE)
    transportadora = models.ForeignKey(Entidades, on_delete=models.PROTECT, null=True, db_constraint=False)

    placa_veiculo = models.CharField(max_length=8, blank=True, null=True)
    uf_veiculo = models.CharField(max_length=2, blank=True, null=True)

    class Meta:
        db_table = "nf_transporte"
        verbose_name = "Transporte Nota Fiscal"
        verbose_name_plural = "Transportes Nota Fiscal"
        indexes = [
            models.Index(fields=["nota"])
        ]


# ------------------------------------------------------------

class NotaEvento(models.Model):
    nota = models.ForeignKey(Nota, related_name="eventos", on_delete=models.CASCADE)

    tipo = models.CharField(max_length=20)  # "cancelamento", "cce"…
    descricao = models.TextField()
    xml = models.TextField(blank=True, null=True)
    protocolo = models.CharField(max_length=60, blank=True, null=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "nf_nota_evento"
        verbose_name = "Evento Nota Fiscal"
        verbose_name_plural = "Eventos Nota Fiscal"
        indexes = [
            models.Index(fields=["nota", "tipo"])
        ]

    def __str__(self):
        return f"Evento {self.tipo} – NF {self.nota.numero}"
