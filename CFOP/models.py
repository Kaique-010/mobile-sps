from django.db import models


CST_ICMS_CHOICES = [
    ('00', 'Tributada integralmente'),
    ('10', 'Tributada e com cobrança do ICMS por substituição tributária'),
    ('20', 'Com redução de base de cálculo'),
    ('30', 'Isenta ou não tributada e com cobrança do ICMS por substituição tributária'),
    ('40', 'Isenta'),
    ('41', 'Não tributada'),
    ('50', 'Suspensão'),
    ('51', 'Diferimento'),
    ('60', 'ICMS cobrado anteriormente por substituição tributária'),
    ('70', 'Com redução de base de cálculo e cobrança do ICMS por substituição tributária'),
    ('90', 'Outras'),
]


CST_PIS_CHOICES = [
    ('01', 'Operação Tributável com Alíquota Básica'),
    ('02', 'Operação Tributável com Alíquota Diferenciada'),
    ('03', 'Operação Tributável com Alíquota por Unidade de Medida'),
    ('04', 'Operação Tributável Monofásica - Alíquota Zero'),
    ('05', 'Operação Tributável por Substituição Tributária'),
    ('06', 'Operação Tributável - Alíquota Zero'),
    ('07', 'Operação Isenta da Contribuição'),
    ('08', 'Operação sem Incidência da Contribuição'),
    ('09', 'Operação com Suspensão da Contribuição'),
    ('49', 'Outras Operações de Saída'),
]


CST_COFINS_CHOICES = [
    ('01', 'Operação Tributável com Alíquota Básica'),
    ('02', 'Operação Tributável com Alíquota Diferenciada'),
    ('03', 'Operação Tributável com Alíquota por Unidade de Medida'),
    ('04', 'Operação Tributável Monofásica - Alíquota Zero'),
    ('05', 'Operação Tributável por Substituição Tributária'),
    ('06', 'Operação Tributável - Alíquota Zero'),
    ('07', 'Operação Isenta da Contribuição'),
    ('08', 'Operação sem Incidência da Contribuição'),
    ('09', 'Operação com Suspensão da Contribuição'),
    ('49', 'Outras Operações de Saída'),
]


CST_IPI_CHOICES = [
    ('00', 'Entrada com Recuperação de Crédito'),
    ('01', 'Entrada Tributada com Alíquota Zero'),
    ('02', 'Entrada Isenta'),
    ('03', 'Entrada Não Tributada'),
    ('04', 'Entrada Imune'),
    ('05', 'Entrada com Suspensão'),
    ('49', 'Outras Entradas'),
    ('50', 'Saída Tributada'),
    ('51', 'Saída Tributada com Alíquota Zero'),
    ('52', 'Saída Isenta'),
    ('53', 'Saída Não Tributada'),
    ('54', 'Saída Imune'),
    ('55', 'Saída com Suspensão'),
    ('99', 'Outras Saídas'),
]

    
CFOP_CHOICES = [
    # Operações de Entrada (Compra)
    ('1101', '1101 - Compra para industrialização'),
    ('1102', '1102 - Compra para comercialização'),
    ('1111', '1111 - Compra para industrialização por encomenda'),
    ('1113', '1113 - Compra para industrialização sob o regime de drawback'),
    ('1116', '1116 - Compra para utilização na prestação de serviço'),
    ('1121', '1121 - Devolução de venda de produção do estabelecimento'),
    ('1122', '1122 - Devolução de venda de mercadoria adquirida ou recebida de terceiros'),
    ('1201', '1201 - Entrada para industrialização por conta e ordem do adquirente da mercadoria, quando esta não transitar pelo estabelecimento do adquirente'),
    ('1202', '1202 - Entrada para industrialização por conta e ordem do adquirente da mercadoria, quando esta transitar pelo estabelecimento do adquirente'),
    ('1301', '1301 - Entrada de mercadoria com previsão de exportação'),
    ('1403', '1403 - Compra para comercialização com substituição tributária'),
    ('2101', '2101 - Compra para industrialização, de mercadoria procedente de outro estado'),
    ('2102', '2102 - Compra para comercialização, de mercadoria procedente de outro estado'),
    ('2103', '2103 - Compra para uso ou consumo, de mercadoria procedente de outro estado'),
    ('2201', '2201 - Devolução de venda de mercadoria adquirida de outro estado'),
    ('2202', '2202 - Devolução de venda de mercadoria adquirida de outro estado, com ICMS devido por substituição tributária'),
    ('2301', '2301 - Compra de mercadoria em consignação, de outro estado'),
    ('2401', '2401 - Entrada de mercadoria importada, de outro estado'),
    ('2701', '2701 - Entrada de mercadoria de fora do estado por conta e ordem de terceiros'),

    # Operações de Saída (Venda)
    ('5101', '5101 - Venda de produção do estabelecimento'),
    ('5102', '5102 - Venda de mercadoria adquirida ou recebida de terceiros'),
    ('5111', '5111 - Venda de produção do estabelecimento sob o regime de drawback'),
    ('5112', '5112 - Venda de mercadoria adquirida ou recebida de terceiros, utilizada em processo de industrialização sob o regime de drawback'),
    ('5113', '5113 - Venda de produção do estabelecimento destinada à Zona Franca de Manaus'),
    ('5114', '5114 - Venda de mercadoria adquirida de terceiros destinada à Zona Franca de Manaus'),
    ('5401', '5401 - Venda de produção do estabelecimento em operação com substituição tributária'),
    ('5403', '5403 - Venda de mercadoria adquirida ou recebida de terceiros em operação com substituição tributária'),
    ('5501', '5501 - Remessa de produção do estabelecimento com fim específico de exportação'),
    ('5502', '5502 - Remessa de mercadoria adquirida ou recebida de terceiros com fim específico de exportação'),
    ('5553', '5553 - Venda de energia elétrica para distribuição ou comercialização'),
    ('5554', '5554 - Venda de energia elétrica para estabelecimento comercial'),
    ('6101', '6101 - Venda de produção do estabelecimento ao consumidor final'),
    ('6102', '6102 - Venda de mercadoria adquirida de terceiros ao consumidor final'),
    ('6108', '6108 - Venda de mercadoria adquirida de terceiros ao consumidor final com isenção de ICMS'),
    ('6110', '6110 - Venda de produção do estabelecimento a empresa do Simples Nacional com isenção de ICMS'),
    ('6124', '6124 - Venda de produção do estabelecimento para industrialização por terceiros'),

    # Outros
    ('5931', '5931 - Prestação de serviço de transporte de carga'),
    ('5932', '5932 - Prestação de serviço de transporte de passageiros'),
    ('6931', '6931 - Prestação de serviço de comunicação'),
    ('6932', '6932 - Prestação de serviço de telecomunicação'),
    ('7949', '7949 - Outras saídas'),
    ('8949', '8949 - Outras entradas'),
]

# Create your models here.
class Cfop(models.Model):
    cfop_empr = models.IntegerField(primary_key=True)
    cfop_codi = models.IntegerField()
    cfop_cfop = models.IntegerField()
    cfop_desc = models.CharField(max_length=60)
    cfop_desc_comp = models.TextField(blank=True, null=True)
    cfop_tipo = models.CharField(max_length=2, blank=True, null=True)
    cfop_moes = models.BooleanField(blank=True, null=True)
    cfop_mofi = models.BooleanField(blank=True, null=True)
    cfop_regi_entr = models.BooleanField(blank=True, null=True)
    cfop_regi_said = models.BooleanField(blank=True, null=True)
    cfop_apur_icms = models.BooleanField(blank=True, null=True)
    cfop_apur_ipi = models.BooleanField(blank=True, null=True)
    cfop_sped = models.BooleanField(blank=True, null=True)
    cfop_icms_prod = models.BooleanField(blank=True, null=True)
    cfop_icms_fret = models.BooleanField(blank=True, null=True)
    cfop_icms_segu = models.BooleanField(blank=True, null=True)
    cfop_icms_desp = models.BooleanField(blank=True, null=True)
    cfop_icms_ipi = models.BooleanField(blank=True, null=True)
    cfop_icms_pis = models.BooleanField(blank=True, null=True)
    cfop_icms_cofi = models.BooleanField(blank=True, null=True)
    cfop_icms_desc = models.BooleanField(blank=True, null=True)
    cfop_ipi_prod = models.BooleanField(blank=True, null=True)
    cfop_ipi_fret = models.BooleanField(blank=True, null=True)
    cfop_ipi_segu = models.BooleanField(blank=True, null=True)
    cfop_ipi_desp = models.BooleanField(blank=True, null=True)
    cfop_ipi_desc = models.BooleanField(blank=True, null=True)
    cfop_icms_isen = models.BooleanField(blank=True, null=True)
    cfop_icms_outr = models.BooleanField(blank=True, null=True)
    cfop_icms_dife = models.BooleanField(blank=True, null=True)
    cfop_ipi_isen = models.BooleanField(blank=True, null=True)
    cfop_ipi_outr = models.BooleanField(blank=True, null=True)
    cfop_ipi_dife = models.BooleanField(blank=True, null=True)
    cfop_pis_prod = models.BooleanField(blank=True, null=True)
    cfop_pis_fret = models.BooleanField(blank=True, null=True)
    cfop_pis_segu = models.BooleanField(blank=True, null=True)
    cfop_pis_desp = models.BooleanField(blank=True, null=True)
    cfop_pis_ipi = models.BooleanField(blank=True, null=True)
    cfop_pis_icms_st = models.BooleanField(blank=True, null=True)
    cfop_pis_desc = models.BooleanField(blank=True, null=True)
    cfop_obse = models.TextField(blank=True, null=True)
    cfop_debi_tota_nota = models.IntegerField(blank=True, null=True)
    cfop_cred_tota_nota = models.IntegerField(blank=True, null=True)
    cfop_debi_icms = models.IntegerField(blank=True, null=True)
    cfop_cred_icms = models.IntegerField(blank=True, null=True)
    cfop_debi_st = models.IntegerField(blank=True, null=True)
    cfop_cred_st = models.IntegerField(blank=True, null=True)
    cfop_debi_ipi = models.IntegerField(blank=True, null=True)
    cfop_cred_ipi = models.IntegerField(blank=True, null=True)
    cfop_debi_pis = models.IntegerField(blank=True, null=True)
    cfop_cred_pis = models.IntegerField(blank=True, null=True)
    cfop_debi_cofi = models.IntegerField(blank=True, null=True)
    cfop_cred_cofi = models.IntegerField(blank=True, null=True)
    cfop_debi_iss = models.IntegerField(blank=True, null=True)
    cfop_cred_iss = models.IntegerField(blank=True, null=True)
    cfop_debi_funr = models.IntegerField(blank=True, null=True)
    cfop_cred_funr = models.IntegerField(blank=True, null=True)
    cfop_debi_pis_reti = models.IntegerField(blank=True, null=True)
    cfop_cred_pis_reti = models.IntegerField(blank=True, null=True)
    cfop_debi_cofi_reti = models.IntegerField(blank=True, null=True)
    cfop_cred_cofi_reti = models.IntegerField(blank=True, null=True)
    cfop_debi_csll_reti = models.IntegerField(blank=True, null=True)
    cfop_cred_csll_reti = models.IntegerField(blank=True, null=True)
    cfop_debi_iss_reti = models.IntegerField(blank=True, null=True)
    cfop_cred_iss_reti = models.IntegerField(blank=True, null=True)
    cfop_debi_irrf_reti = models.IntegerField(blank=True, null=True)
    cfop_cred_irrf_reti = models.IntegerField(blank=True, null=True)
    cfop_debi_inss_reti = models.IntegerField(blank=True, null=True)
    cfop_cred_inss_reti = models.IntegerField(blank=True, null=True)
    cfop_circ_merc = models.BooleanField(blank=True, null=True)
    cfop_trib_redu = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_trib_icms = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_trib_moda_base = models.CharField(max_length=1, blank=True, null=True)
    cfop_trib_moda_bast = models.CharField(max_length=1, blank=True, null=True)
    cfop_trib_mva = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_trib_redu_st = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_trib_ipi_trib = models.CharField(max_length=2, blank=True, null=True)
    cfop_trib_ipi_nao_trib = models.CharField(max_length=2, blank=True, null=True)
    cfop_trib_aliq_ipi = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_trib_cst_pis = models.CharField(max_length=2, blank=True, null=True)
    cfop_trib_perc_pis = models.DecimalField(max_digits=5, decimal_places=4, blank=True, null=True)
    cfop_trib_valo_pis = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    cfop_trib_cst_cofins = models.CharField(max_length=2, blank=True, null=True)
    cfop_trib_perc_cofins = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_trib_valo_cofins = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    cfop_trib_orig_merc = models.CharField(max_length=1, blank=True, null=True)
    cfop_trib_cst_icms = models.CharField(max_length=3, blank=True, null=True)
    cfop_soli_cont_debi_tota = models.BooleanField(blank=True, null=True)
    cfop_soli_cont_cred_tota = models.BooleanField(blank=True, null=True)
    cfop_obri_cont = models.BooleanField(blank=True, null=True)
    cfop_sped_cofi = models.BooleanField(blank=True, null=True)
    cfop_nao_calc_impo = models.BooleanField(blank=True, null=True)
    cfop_apur_pis = models.BooleanField(blank=True, null=True)
    cfop_apur_cofi = models.BooleanField(blank=True, null=True)
    cfop_nao_trib_icms = models.BooleanField(blank=True, null=True)
    cfop_nao_trib_ipi = models.BooleanField(blank=True, null=True)
    cfop_nao_trib_pis = models.BooleanField(blank=True, null=True)
    cfop_list_serv = models.BooleanField(blank=True, null=True)
    cfop_dife_parc = models.BooleanField(blank=True, null=True)
    cfop_sem_icms = models.IntegerField(blank=True, null=True)
    cfop_sem_ipi = models.IntegerField(blank=True, null=True)
    cfop_inat = models.BooleanField(blank=True, null=True)
    cfop_437 = models.CharField(max_length=2, blank=True, null=True)
    cfop_fina_cfop = models.CharField(max_length=2, blank=True, null=True)
    cfop_inic_vali = models.DateField(blank=True, null=True)
    cfop_fim_vali = models.DateField(blank=True, null=True)
    cfop_cred_icms_simp = models.BooleanField(blank=True, null=True)
    cfop_debi_pis_mono = models.IntegerField(blank=True, null=True)
    cfop_cred_pis_mono = models.IntegerField(blank=True, null=True)
    cfop_debi_cofi_mono = models.IntegerField(blank=True, null=True)
    cfop_cred_cofi_mono = models.IntegerField(blank=True, null=True)
    cfop_iss_aliq = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_pis_aliq = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_cof_aliq = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_iss_ret = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_pis_ret = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_cof_ret = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_csl_ret = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_irr_ret = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_ins_ret = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_bas_ins = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_bas_irr = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_436 = models.CharField(max_length=3, blank=True, null=True)
    cfop_segu_atm = models.BooleanField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.
    cfop_linh_gia = models.IntegerField(blank=True, null=True)
    cfop_base_irpj = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    cfop_perc_irpj = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    cfop_base_csll = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    cfop_perc_csll = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    cfop_debi_irpj = models.IntegerField(blank=True, null=True)
    cfop_cred_irpj = models.IntegerField(blank=True, null=True)
    cfop_debi_csllp = models.IntegerField(blank=True, null=True)
    cfop_cred_csllp = models.IntegerField(blank=True, null=True)
    cfop_redu_icms_para = models.BooleanField(blank=True, null=True)
    cfop_rela_fatu_simp = models.BooleanField(blank=True, null=True)
    cfop_obri_refe = models.BooleanField(blank=True, null=True)
    cfop_nao_soma_mva = models.BooleanField(blank=True, null=True)
    cfop_conf_vend_st = models.BooleanField(blank=True, null=True)
    cfop_icms_st_ipi = models.BooleanField(blank=True, null=True)
    cfop_boni_desc = models.BooleanField(blank=True, null=True)
    cfop_debi_mate_prim = models.IntegerField(blank=True, null=True)
    cfop_cred_esto_fina = models.IntegerField(blank=True, null=True)
    cfop_debi_esto_inic = models.IntegerField(blank=True, null=True)
    cfop_cred_prod_acab = models.IntegerField(blank=True, null=True)
    cfop_pis_cofi_icms = models.BooleanField(blank=True, null=True)
    cfop_nao_gera_cust_agri = models.BooleanField(blank=True, null=True)
    cfop_perc_dife_aliq = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_bene_fisc = models.CharField(max_length=10, blank=True, null=True)
    
    #Campos CBS e IBS
    cfop_ibscbs_cclasstrib = models.CharField(max_length=6, blank=True, null=True)
    cfop_ibscbs_cst = models.CharField(max_length=3, blank=True, null=True)
    cfop_ibs_pdifuf = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_ibs_preduf = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_ibs_paliqefetuf = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_ibs_pibsuf = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_ibs_pdifmun = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_ibs_paliqefetmun = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_ibs_predmun = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_ibs_pibsmun = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_cbs_pdif = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_cbs_paliqefet = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_cbs_pred = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_cbs_pcbs = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_adremcbsret = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_adremibsret = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_cbs_paliqefetreg = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_ibs_paliqefetmunreg = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_ibs_paliqefetufreg = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cfop_ibscbs_cclasstribreg = models.CharField(max_length=6, blank=True, null=True)
    cfop_ibscbs_cstreg = models.CharField(max_length=3, blank=True, null=True)
    cfop_ibscbs_cstid = models.IntegerField(blank=True, null=True)
    cfop_ibscbs_cstregid = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cfop'
        unique_together = (('cfop_empr', 'cfop_codi'),)

class CfopSearchHistory(models.Model):
    empresa_id = models.IntegerField(blank=True, null=True)
    usuario_id = models.IntegerField(blank=True, null=True)
    query = models.CharField(max_length=120)
    uf = models.CharField(max_length=2, blank=True, null=True)
    tipo = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'cfop_search_history'