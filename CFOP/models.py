from django.db import models
from django.core.exceptions import ValidationError
from Produtos.models import Ncm, Produtos
from .defaults_cfop import CFOP_DEFAULTS, deduzir_defaults
import re

class CFOPFiscal(models.Model):
    cfop_codi = models.CharField(primary_key=True, max_length=4, verbose_name="Código")
    cfop_desc = models.TextField(verbose_name="Descrição")

    class Meta:
        db_table = 'cfopfiscal'
        managed = False
        verbose_name = "CFOP Fiscal (Consulta)"
        verbose_name_plural = "CFOPs Fiscais (Consulta)"

    def __str__(self):
        return f"{self.cfop_codi} - {self.cfop_desc}"
    
    
class CFOP(models.Model):
    cfop_id = models.AutoField(primary_key=True)
    cfop_empr = models.IntegerField(verbose_name="Empresa", help_text="ID da empresa vinculada")
    cfop_codi = models.CharField(max_length=10, unique=True, verbose_name="Código CFOP", help_text="Código fiscal de operação (ex: 5102). Deve ter 4 dígitos.")
    cfop_desc = models.CharField(max_length=255, verbose_name="Descrição", help_text="Descrição da operação")

    # FLAGS DE EXIGÊNCIA
    cfop_exig_ipi = models.BooleanField(default=False, verbose_name="Exige IPI", help_text="Calcula e destaca IPI na nota")
    cfop_exig_icms = models.BooleanField(default=False, verbose_name="Exige ICMS", help_text="Calcula e destaca ICMS na nota")
    cfop_exig_pis_cofins = models.BooleanField(default=False, verbose_name="Exige PIS/COFINS", help_text="Calcula e destaca PIS/COFINS na nota")
    cfop_exig_cbs = models.BooleanField(default=False, verbose_name="Exige CBS", help_text="Calcula CBS (Reforma Tributária)")
    cfop_exig_ibs = models.BooleanField(default=False, verbose_name="Exige IBS", help_text="Calcula IBS (Reforma Tributária)")

    # FLAGS DE GERAÇÃO
    cfop_gera_st = models.BooleanField(default=False, verbose_name="Gera ST", help_text="Calcula Substituição Tributária")
    cfop_gera_difal = models.BooleanField(default=False, verbose_name="Gera DIFAL", help_text="Calcula Diferencial de Alíquota")
    
    # BASES DE CÁLCULO
    cfop_icms_base_inclui_ipi = models.BooleanField(default=False, verbose_name="Base ICMS inclui IPI", help_text="Adiciona valor do IPI na base do ICMS")
    cfop_st_base_inclui_ipi = models.BooleanField(default=False, verbose_name="Base ST inclui IPI", help_text="Adiciona valor do IPI na base do ST")
    
    # TOTALIZA NAS NOTAS FISCAIS
    cfop_ipi_tota_nf = models.BooleanField(default=False, verbose_name="IPI compõe Total NF", help_text="Soma o valor do IPI ao total da nota")
    cfop_st_tota_nf = models.BooleanField(default=False, verbose_name="ST compõe Total NF", help_text="Soma o valor do ST ao total da nota")

    class Meta:
        db_table = "cfopweb"
        ordering = ["cfop_codi"]
        verbose_name = "CFOP"
        verbose_name_plural = "CFOPs"

    def __str__(self):
        return f"{self.cfop_codi} - {self.cfop_desc}"

    def clean(self):
        # Validação do código (deve ser numérico e ter 4 dígitos)
        # Nota: cfop_codi é CharField(10) por legado, mas a regra é 4 dígitos
        if self.cfop_codi:
            cod = self.cfop_codi.strip()
            if not cod.isdigit() or len(cod) != 4:
                raise ValidationError({"cfop_codi": "O CFOP deve conter exatamente 4 dígitos numéricos."})
            
            # Validação do primeiro dígito (1, 2, 3 entrada; 5, 6, 7 saída)
            first_digit = int(cod[0])
            if first_digit not in [1, 2, 3, 5, 6, 7]:
                raise ValidationError({"cfop_codi": f"CFOP iniciado em {first_digit} não é válido (Use 1,2,3 para entrada ou 5,6,7 para saída)."})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def aplicar_defaults(self, regime: str | None = None):
        c = str(self.cfop_codi or "").strip()
        if not c:
            return
        defaults = deduzir_defaults(c, regime)

        self.cfop_exig_icms       = defaults.get("icms", False)
        self.cfop_exig_ipi        = defaults.get("ipi", False)
        self.cfop_exig_pis_cofins = defaults.get("pis_cofins", False)
        self.cfop_exig_cbs        = defaults.get("cbs", False)
        self.cfop_exig_ibs        = defaults.get("ibs", False)
        self.cfop_gera_st         = defaults.get("st", False)
        self.cfop_gera_difal      = defaults.get("difal", False)
        self.cfop_icms_base_inclui_ipi = defaults.get("icms_base_inclui_ipi", False)
        self.cfop_st_base_inclui_ipi = defaults.get("st_base_inclui_ipi", False)
        self.cfop_ipi_tota_nf = defaults.get("ipi_tota_nf", False)
        self.cfop_st_tota_nf = defaults.get("st_tota_nf", False)



    @property
    def exigencias(self):
        itens = []

        if self.cfop_exig_icms:
            itens.append("ICMS")

        if self.cfop_exig_ipi:
            itens.append("IPI")

        if self.cfop_exig_pis_cofins:
            itens.append("PIS/COFINS")

        if self.cfop_gera_st:
            itens.append("ICMS-ST")

        if self.cfop_gera_difal:
            itens.append("DIFAL")

        if self.cfop_exig_cbs:
            itens.append("CBS")

        if self.cfop_exig_ibs:
            itens.append("IBS")

        return itens

class MapaCFOP(models.Model):
    TIPO_OPER = [
        ("VENDA", "Venda"),
        ("COMPRA", "Compra"),
        ("DEVOLUCAO_VENDA", "Devolução de Venda"),
        ("DEVOLUCAO_COMPRA", "Devolução de Compra"),
        ("REMESSA", "Remessa"),
        ("TRANSFERENCIA", "Transferência"),
        ("BONIFICACAO", "Bonificação"),
        ("EXPORTACAO", "Exportação"),
    ]

    tipo_oper = models.CharField(max_length=30, choices=TIPO_OPER)
    uf_origem = models.CharField(max_length=2)
    uf_destino = models.CharField(max_length=2)

    cfop = models.ForeignKey(CFOP, on_delete=models.PROTECT)

    class Meta:
        unique_together = ('tipo_oper', 'uf_origem', 'uf_destino')
        db_table = "mapa_cfop"

    def __str__(self):
        return f"{self.tipo_oper}: {self.uf_origem}->{self.uf_destino} → {self.cfop.cfop_codi}"

class TabelaICMS(models.Model):
    id = models.AutoField(primary_key=True, db_column='tabe_id')
    uf_origem = models.CharField(max_length=2, db_column='tabe_uf_orig')
    uf_destino = models.CharField(max_length=2, db_column='tabe_uf_dest')
    empresa = models.IntegerField(db_column='tabe_empr')
    aliq_interna = models.DecimalField(max_digits=5, decimal_places=2, db_column='tabe_aliq_interna')
    aliq_inter = models.DecimalField(max_digits=5, decimal_places=2, db_column='tabe_aliq_inter')
    mva_st = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, db_column='tabe_mva_st')

    class Meta:
        unique_together = ('empresa', 'uf_origem', 'uf_destino')
        db_table = "tabela_icms"

    def __str__(self):
        return f"{self.tabe_empr}: {self.tebe_uf_orig} → {self.tabe_uf_dest}"


class NCM_CFOP_DIF(models.Model):
    ncmdif_id = models.AutoField(primary_key=True)
    ncm_empr = models.IntegerField()
    ncm = models.ForeignKey(Ncm, on_delete=models.CASCADE, db_constraint=False)
    cfop = models.ForeignKey(CFOP, on_delete=models.CASCADE)

    # overrides
    ncm_ipi_dif = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    ncm_pis_dif = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    ncm_cofins_dif = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    ncm_cbs_dif = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    ncm_ibs_dif = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    ncm_icms_aliq_dif = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    ncm_st_aliq_dif = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('ncm', 'cfop')
        db_table = "ncm_cfop_dif"

    def __str__(self):
        return f"Diferencial {self.ncm.ncm_codi} / {self.cfop.cfop_codi}"




class FiscalPadraoBase(models.Model):
    class Meta:
        abstract = True

    # CSTs
    cst_icms = models.CharField(max_length=3, null=True, blank=True)
    cst_ipi = models.CharField(max_length=3, null=True, blank=True)
    cst_pis = models.CharField(max_length=3, null=True, blank=True)
    cst_cofins = models.CharField(max_length=3, null=True, blank=True)
    cst_cbs = models.CharField(max_length=3, null=True, blank=True)
    cst_ibs = models.CharField(max_length=3, null=True, blank=True)

    # Alíquotas override
    aliq_icms = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    aliq_ipi = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    aliq_pis = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    aliq_cofins = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    aliq_cbs = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    aliq_ibs = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    def aplicar(self, ctx, resultado):
        # override explícito
        for tributo in resultado.aliquotas:
            v = getattr(self, f"aliq_{tributo}", None)
            if v is not None:
                resultado.aliquotas[tributo] = v

class NcmFiscalPadrao(FiscalPadraoBase):
    ncm = models.OneToOneField(Ncm, on_delete=models.CASCADE, related_name="fiscal", db_constraint=False)


    class Meta:
        db_table = "ncm_fiscal_padrao"
        verbose_name = "Fiscal Padrão NCM"
        verbose_name_plural = "Fiscais Padrão NCM"


class ProdutoFiscalPadrao(FiscalPadraoBase):
    produto = models.OneToOneField(Produtos, on_delete=models.CASCADE, related_name="fiscal", db_constraint=False)


    class Meta:
        db_table = "produto_fiscal_padrao"
        verbose_name = "Fiscal Padrão Produto"
        verbose_name_plural = "Fiscais Padrão Produto"