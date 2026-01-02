from django.db import models
from Produtos.models import Ncm
from .defaults_cfop import CFOP_DEFAULTS, deduzir_defaults


class CFOPFiscal(models.Model):
    cfop_codi = models.CharField(primary_key=True, max_length=4)
    cfop_desc = models.TextField()

    class Meta:
        db_table = 'cfopfiscal'
        managed = False

    def __str__(self):
        return f"{self.cfop_codi} - {self.cfop_desc}"
    
class CFOP(models.Model):
    cfop_id = models.AutoField(primary_key=True)
    cfop_empr = models.IntegerField()
    cfop_codi = models.CharField(max_length=10, unique=True)
    cfop_desc = models.CharField(max_length=255)

    # FLAGS
    cfop_exig_ipi = models.BooleanField(default=False)
    cfop_exig_icms = models.BooleanField(default=False)
    cfop_exig_pis_cofins = models.BooleanField(default=False)
    cfop_exig_cbs = models.BooleanField(default=False)
    cfop_exig_ibs = models.BooleanField(default=False)

    cfop_gera_st = models.BooleanField(default=False)
    cfop_gera_difal = models.BooleanField(default=False)

    class Meta:
        db_table = "cfopweb"

    def __str__(self):
        return f"{self.cfop_codi} - {self.cfop_desc}"


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

 
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


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
    ncm = models.ForeignKey(Ncm, on_delete=models.CASCADE)
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
