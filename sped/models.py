from django.db import models

# Create your models here.
class Filial(models.Model):
    empr_empr = models.IntegerField(primary_key=True, db_column='empr_empr')
    empr_codi = models.IntegerField(db_column='empr_codi', blank=True, null=True)
    empr_nome = models.CharField(max_length=100, db_column='empr_nome')
    empr_docu = models.CharField(max_length=14, unique=True, db_column='empr_cnpj')
    empr_insc_esta = models.CharField(max_length=30, blank=True, null=True)
    empr_cep = models.CharField(max_length=8, blank=True, null=True)
    empr_ende = models.CharField(max_length=60, blank=True, null=True)
    empr_nume = models.CharField(max_length=10, blank=True, null=True)
    empr_comp = models.CharField(max_length=20, blank=True, null=True)
    empr_bair = models.CharField(max_length=60, blank=True, null=True)
    empr_cida = models.CharField(max_length=60, blank=True, null=True)
    empr_esta = models.CharField(max_length=2, blank=True, null=True)
    empr_fone = models.CharField(max_length=14, blank=True, null=True)
    empr_celu = models.CharField(max_length=14, blank=True, null=True)
    empr_emai = models.CharField(max_length=100, blank=True, null=True)
    empr_codi_cida = models.CharField(max_length=7, blank=True, null=True)
    empr_codi_cont = models.IntegerField(blank=True, null=True)
    empr_perf_sped = models.CharField(max_length=1, blank=True, null=True)
    empr_ativ_sped = models.CharField(max_length=1, blank=True, null=True)
    
    def __str__(self):
        return self.empr_nome
    class Meta:
        db_table = 'filiais'
        managed = False
        
        
class Contadores(models.Model):
    cont_codi    = models.BigIntegerField(primary_key=True)
    cont_nome = models.CharField(max_length=100, default='')  
    cont_cpf = models.CharField(max_length=11, blank=True, null=True)  
    cont_cnpj = models.CharField(max_length=14, blank=True, null=True)   
    cont_cep = models.CharField(max_length=8) 
    cont_ende = models.CharField(max_length=60)
    cont_nume = models.CharField(max_length=10)  
    cont_comp = models.CharField(max_length=60, blank=True, null=True)
    cont_cida = models.CharField(max_length=60)
    cont_esta = models.CharField(max_length=2)
    cont_pais = models.CharField(max_length=60, default='1058')
    cont_codi_pais = models.CharField(max_length=6, default='1058')
    cont_crc = models.CharField(max_length=15, blank=True, null=True)
    cont_emai = models.CharField(max_length=100, blank=True, null=True)
    cont_fone = models.CharField(max_length=14, blank=True, null=True)  
    cont_celu = models.CharField(max_length=14, blank=True, null=True)  
    
    def __str__(self):
        return self.cont_nome
    
    class Meta:
        db_table = 'contadores'
        managed = False

class Entidades(models.Model):
    enti_empr = models.IntegerField()
    enti_clie = models.BigIntegerField(unique=True, primary_key=True)
    enti_nome = models.CharField(max_length=100, default='')  
    enti_tipo_enti = models.CharField(max_length=100, blank=True, null=True)
    enti_cpf = models.CharField(max_length=11, blank=True, null=True)  
    enti_cnpj = models.CharField(max_length=14, blank=True, null=True)  
    enti_insc_esta = models.CharField(max_length=14, blank=True, null=True)    
    enti_cep = models.CharField(max_length=8) 
    enti_ende = models.CharField(max_length=60)
    enti_nume = models.CharField(max_length=10)  
    enti_comp = models.CharField(max_length=60, blank=True, null=True)
    enti_cida = models.CharField(max_length=60)
    enti_esta = models.CharField(max_length=2)
    enti_pais = models.CharField(max_length=60, default='1058')
    enti_codi_pais = models.CharField(max_length=6, default='1058')
    enti_codi_cida = models.CharField(max_length=7, default='0000000')
    enti_bair = models.CharField(max_length=60)
    enti_fone = models.CharField(max_length=14, blank=True, null=True)  
    enti_celu = models.CharField(max_length=15, blank=True, null=True)  
    enti_emai = models.CharField(max_length=100, blank=True, null=True)  
    

    def __str__(self):
        return self.enti_nome
    class Meta:
        db_table = 'entidades'
        managed = False


class UnidadeMedida(models.Model):
    unid_codi = models.CharField(max_length=10, primary_key=True)
    unid_desc = models.CharField(max_length=100)
    
    def __str__(self):
        return self.unid_desc
    class Meta:
        db_table = 'unidadesmedidas'
        managed = False
        


class Produtos(models.Model):
    prod_empr = models.CharField(max_length=50, db_column='prod_empr')
    prod_codi = models.CharField(max_length=50, db_column='prod_codi', primary_key=True) 
    prod_nome = models.CharField(max_length=255, db_column='prod_nome') 
    prod_unme = models.ForeignKey(UnidadeMedida,on_delete=models.PROTECT, db_column='prod_unme') 
    prod_ncm = models.CharField(max_length=10, db_column='prod_ncm', blank= True, null= True) 
    prod_orig_merc = models.CharField(max_length=1, db_column='prod_orig_merc', blank=True, null=True, default='0')
    

    class Meta:
        db_table = 'produtos'
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        managed = False

    def __str__(self):
        return self.prod_codi


class CFOP(models.Model):
    cfop_id = models.AutoField(primary_key=True)
    cfop_empr = models.IntegerField(verbose_name="Empresa", help_text="ID da empresa vinculada")
    cfop_codi = models.CharField(max_length=10, unique=True, verbose_name="Código CFOP", help_text="Código fiscal de operação (ex: 5102). Deve ter 4 dígitos.")
    cfop_desc = models.CharField(max_length=255, verbose_name="Descrição", help_text="Descrição da operação")




class Nfevv(models.Model):
    a02_versao = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    a03_id = models.CharField(max_length=47, blank=True, null=True)
    b02_cuf_emi = models.IntegerField(blank=True, null=True)
    b03_cnf = models.IntegerField(blank=True, null=True)
    b04_natop = models.CharField(max_length=60, blank=True, null=True)
    b05_indpag = models.IntegerField(blank=True, null=True)
    b06_mod = models.CharField(max_length=2, blank=True, null=True)
    b07_serie = models.CharField(max_length=3, blank=True, null=True)
    b08_nnf = models.IntegerField(blank=True, null=True)
    b09_demi = models.DateField(blank=True, null=True)
    b10_dsaient = models.DateField(blank=True, null=True)
    b10a_hsaient = models.TimeField(blank=True, null=True)
    b11_tpnf = models.IntegerField(blank=True, null=True)
    b12_cmunfg = models.IntegerField(blank=True, null=True)
    b21_tplmp = models.IntegerField(blank=True, null=True)
    b22_tpemis = models.IntegerField(blank=True, null=True)
    b23_cdv = models.IntegerField(blank=True, null=True)
    b24_tpamb = models.IntegerField(blank=True, null=True)
    b25_finnfe = models.IntegerField(blank=True, null=True)
    b26_procemi = models.IntegerField(blank=True, null=True)
    b27_verproc = models.CharField(max_length=20, blank=True, null=True)
    b28_dhcont = models.DateField(blank=True, null=True)
    b29_xjust = models.TextField(blank=True, null=True)
    c02_cnpj = models.CharField(max_length=14, blank=True, null=True)
    c02a_cpf = models.CharField(max_length=11, blank=True, null=True)
    c03_xnome = models.CharField(max_length=60, blank=True, null=True)
    c04_xfant = models.CharField(max_length=60, blank=True, null=True)
    c06_xlgr = models.CharField(max_length=60, blank=True, null=True)
    c07_nro = models.CharField(max_length=60, blank=True, null=True)
    c08_xcpl = models.CharField(max_length=60, blank=True, null=True)
    c09_xbairro = models.CharField(max_length=60, blank=True, null=True)
    c10_cmun = models.IntegerField(blank=True, null=True)
    c11_xmun = models.CharField(max_length=60, blank=True, null=True)
    c12_uf = models.CharField(max_length=2, blank=True, null=True)
    c13_cep = models.IntegerField(blank=True, null=True)
    c14_cpais = models.IntegerField(blank=True, null=True)
    c15_xpais = models.CharField(max_length=60, blank=True, null=True)
    c16_fone = models.CharField(max_length=15, blank=True, null=True)
    c17_ie = models.CharField(max_length=14, blank=True, null=True)
    c18_iest = models.CharField(max_length=14, blank=True, null=True)
    c19_im = models.CharField(max_length=15, blank=True, null=True)
    c20_cnae = models.CharField(max_length=7, blank=True, null=True)
    c21_crt = models.IntegerField(blank=True, null=True)
    e02_cnpj = models.CharField(max_length=14, blank=True, null=True)
    e03_cpf = models.CharField(max_length=11, blank=True, null=True)
    e04_xnome = models.CharField(max_length=60, blank=True, null=True)
    e06_xlgr = models.CharField(max_length=60, blank=True, null=True)
    e07_nro = models.CharField(max_length=60, blank=True, null=True)
    e08_xcpl = models.CharField(max_length=60, blank=True, null=True)
    e09_xbairro = models.CharField(max_length=60, blank=True, null=True)
    e10_cmun = models.IntegerField(blank=True, null=True)
    e11_xmun = models.CharField(max_length=60, blank=True, null=True)
    e12_uf = models.CharField(max_length=2, blank=True, null=True)
    e13_cep = models.IntegerField(blank=True, null=True)
    e14_cpais = models.IntegerField(blank=True, null=True)
    e15_xpais = models.CharField(max_length=60, blank=True, null=True)
    e16_fone = models.CharField(max_length=15, blank=True, null=True)
    e17_ie = models.CharField(max_length=14, blank=True, null=True)
    e18_isuf = models.CharField(max_length=9, blank=True, null=True)
    e19_email = models.CharField(max_length=60, blank=True, null=True)
    f02_cnpj = models.CharField(max_length=14, blank=True, null=True)
    f02a_cpf = models.CharField(max_length=11, blank=True, null=True)
    f03_xlgr = models.CharField(max_length=60, blank=True, null=True)
    f04_nro = models.CharField(max_length=60, blank=True, null=True)
    f05_xcpl = models.CharField(max_length=60, blank=True, null=True)
    f06_xbairro = models.CharField(max_length=60, blank=True, null=True)
    f07_cmun = models.IntegerField(blank=True, null=True)
    f08_xmun = models.CharField(max_length=60, blank=True, null=True)
    f09_uf = models.CharField(max_length=2, blank=True, null=True)
    g02_cnpj = models.CharField(max_length=14, blank=True, null=True)
    g02a_cpf = models.CharField(max_length=11, blank=True, null=True)
    g03_xlgr = models.CharField(max_length=60, blank=True, null=True)
    g04_nro = models.CharField(max_length=60, blank=True, null=True)
    g05_xcpl = models.CharField(max_length=60, blank=True, null=True)
    g06_xbarirro = models.CharField(max_length=60, blank=True, null=True)
    g07_cmun = models.IntegerField(blank=True, null=True)
    g08_xmun = models.CharField(max_length=60, blank=True, null=True)
    g09_uf = models.CharField(max_length=2, blank=True, null=True)
    w03_vbc_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w04_vicms_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w05_vbcst_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w06_vst_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w07_vprod_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w08_vfret_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w09_vseg_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w10_vdesc_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w11_vii_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w12_vipi_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w13_vpis_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w14_vcofins_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w15_voutro_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w16_vnf_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w18_vserv_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w19_vbc_iss_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w20_viss_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w21_vpis_serv = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w22_vcofins_serv = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w24_vretpis = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w25_vretcofins = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w26_vretcsll = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w27_vbcirrf = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w28_virrf = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w29_vbcretprev = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    w30_vretprev = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    x02_modfrete = models.IntegerField(blank=True, null=True)
    x04_cnpj_transp = models.CharField(max_length=14, blank=True, null=True)
    x05_cpf_transp = models.CharField(max_length=11, blank=True, null=True)
    x06_xnome_transp = models.CharField(max_length=60, blank=True, null=True)
    x07_ie_transp = models.CharField(max_length=14, blank=True, null=True)
    x08_xender_transp = models.CharField(max_length=60, blank=True, null=True)
    x09_xmun_transp = models.CharField(max_length=60, blank=True, null=True)
    x10_uf_transp = models.CharField(max_length=2, blank=True, null=True)
    x12_vserv_transp = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    x13_vbcret_transp = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    x14_picmsret_transp = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    x15_vicmsret_transp = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    x16_cfop_transp = models.IntegerField(blank=True, null=True)
    x17_cmunfg_transp = models.IntegerField(blank=True, null=True)
    x19_placa_veic = models.CharField(max_length=8, blank=True, null=True)
    x20_uf_veic = models.CharField(max_length=2, blank=True, null=True)
    x21_rntc_veic = models.CharField(max_length=20, blank=True, null=True)
    x23_placa_reboque1 = models.CharField(max_length=8, blank=True, null=True)
    x24_uf_reboque1 = models.CharField(max_length=2, blank=True, null=True)
    x25_rntc_reboque1 = models.CharField(max_length=20, blank=True, null=True)
    x23_placa_reboque2 = models.CharField(max_length=8, blank=True, null=True)
    x24_uf_reboque2 = models.CharField(max_length=2, blank=True, null=True)
    x25_rntc_reboque2 = models.CharField(max_length=20, blank=True, null=True)
    x23_placa_reboque3 = models.CharField(max_length=8, blank=True, null=True)
    x24_uf_reboque3 = models.CharField(max_length=2, blank=True, null=True)
    x25_rntc_reboque3 = models.CharField(max_length=20, blank=True, null=True)
    x23_placa_reboque4 = models.CharField(max_length=8, blank=True, null=True)
    x24_uf_reboque4 = models.CharField(max_length=2, blank=True, null=True)
    x25_rntc_reboque4 = models.CharField(max_length=20, blank=True, null=True)
    x23_placa_reboque5 = models.CharField(max_length=8, blank=True, null=True)
    x24_uf_reboque5 = models.CharField(max_length=2, blank=True, null=True)
    x25_rntc_reboque5 = models.CharField(max_length=20, blank=True, null=True)
    x25a_vagao = models.CharField(max_length=20, blank=True, null=True)
    x25b_balsa = models.CharField(max_length=20, blank=True, null=True)
    empresa = models.IntegerField(blank=True, null=True)
    filial = models.IntegerField(blank=True, null=True)
    cliente = models.IntegerField(blank=True, null=True)
    xml_nfe = models.TextField(blank=True, null=True)
    prot_nfe = models.CharField(max_length=50, blank=True, null=True)
    status_nfe = models.IntegerField(blank=True, null=True)
    xml_canc = models.TextField(blank=True, null=True)
    prot_canc = models.CharField(max_length=50, blank=True, null=True)
    cancelada = models.BooleanField(blank=True, null=True)
    status_canc = models.IntegerField(blank=True, null=True)
    xml_inut = models.TextField(blank=True, null=True)
    inutilizada = models.BooleanField(blank=True, null=True)
    status_inut = models.IntegerField(blank=True, null=True)
    denegada = models.BooleanField(blank=True, null=True)
    tipo_emissao = models.CharField(max_length=1, blank=True, null=True)
    transportadora = models.IntegerField(blank=True, null=True)
    nfve_mens = models.IntegerField(blank=True, null=True)
    nfev_comp_mens = models.TextField(blank=True, null=True)
    nfev_mens_fisc = models.IntegerField(blank=True, null=True)
    nfev_comp_fisc = models.TextField(blank=True, null=True)
    nfev_veic = models.IntegerField(blank=True, null=True)
    vtottrib = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    vpertrib = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    nrcontrato = models.IntegerField(blank=True, null=True)
    form_reci = models.CharField(max_length=30, blank=True, null=True)
    cfop_pred = models.CharField(max_length=4, blank=True, null=True)
    nume_peve = models.IntegerField(blank=True, null=True)
    vendedor = models.IntegerField(blank=True, null=True)
    base_funr = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    valo_funr = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    avis_baix_auto = models.BooleanField(blank=True, null=True)
    adto_pedi = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.
    ende_entr = models.IntegerField(blank=True, null=True)
    nfev_audi = models.BooleanField(blank=True, null=True)
    nfev_audi_data = models.DateField(blank=True, null=True)
    nfev_audi_por = models.IntegerField(blank=True, null=True)
    nfev_quan_cont = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    nfev_com_os_refe = models.BooleanField(blank=True, null=True)
    nfev_esta_emba = models.CharField(max_length=2, blank=True, null=True)
    nfev_loca_emba = models.CharField(max_length=60, blank=True, null=True)
    nfev_cond = models.IntegerField(blank=True, null=True)
    nume_rece = models.CharField(max_length=30, blank=True, null=True)
    nfev_nume_os = models.TextField(blank=True, null=True)
    nfev_moti_canc_inut = models.CharField(max_length=60, blank=True, null=True)
    usuario = models.IntegerField(blank=True, null=True)
    troco = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    nfev_usua_canc = models.IntegerField(blank=True, null=True)
    lote_nfce = models.CharField(max_length=10, blank=True, null=True)
    nfev_data_hora = models.CharField(max_length=20, blank=True, null=True)
    impo_xml_devo = models.BooleanField(blank=True, null=True)
    nfev_ecf_refe_mode = models.CharField(max_length=2, blank=True, null=True)
    nfev_ecf_refe_nume = models.CharField(max_length=3, blank=True, null=True)
    nfev_ecf_refe_coo = models.CharField(max_length=6, blank=True, null=True)
    nfev_data_base = models.DateField(blank=True, null=True)
    b25a_indfinal = models.IntegerField(blank=True, null=True)
    b25b_indpres = models.IntegerField(blank=True, null=True)
    vicmsdeson = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    nfev_id_dest = models.IntegerField(blank=True, null=True)
    nfev_oper_cart = models.IntegerField(blank=True, null=True)
    valo_impo_fede = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    valo_impo_esta = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    perc_impo_fede = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    perc_impo_esta = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    valo_outr_ipi = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    nfev_prat = models.IntegerField(blank=True, null=True)
    nfev_mens_pind = models.CharField(max_length=250, blank=True, null=True)
    nota_admi_cart = models.IntegerField(blank=True, null=True)
    nota_acer_peso = models.IntegerField(blank=True, null=True)
    nota_de_comp = models.BooleanField(blank=True, null=True)
    ind_intermed = models.BooleanField(blank=True, null=True)
    docu_intermed = models.CharField(max_length=14, blank=True, null=True)
    desc_intermed = models.CharField(max_length=60, blank=True, null=True)
    f02b_xnome = models.CharField(max_length=60, blank=True, null=True)
    f10_cep = models.CharField(max_length=8, blank=True, null=True)
    f13_fone = models.CharField(max_length=14, blank=True, null=True)
    f15_ie = models.CharField(max_length=14, blank=True, null=True)
    g02b_xnome = models.CharField(max_length=60, blank=True, null=True)
    g10_cep = models.CharField(max_length=8, blank=True, null=True)
    g13_fone = models.CharField(max_length=14, blank=True, null=True)
    g15_ie = models.CharField(max_length=14, blank=True, null=True)
    nfev_moto_nome = models.CharField(max_length=60, blank=True, null=True)
    nfev_moto_cpf = models.CharField(max_length=14, blank=True, null=True)
    nfev_moto_cnh = models.CharField(max_length=20, blank=True, null=True)
    nfev_moto_rg = models.CharField(max_length=14, blank=True, null=True)
    nfev_moto_plac = models.CharField(max_length=10, blank=True, null=True)
    nfev_moto_tick = models.CharField(max_length=20, blank=True, null=True)
    nreceituario = models.CharField(max_length=30, blank=True, null=True)
    cpfresptec = models.CharField(max_length=11, blank=True, null=True)
    vtotabcibscbs = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    vtotavdifibsuf = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    vtotavdevibsuf = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    vtotavibsuf = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    vtotavdifibsmun = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    vtotavdevibsmun = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    vtotavibsmun = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    vtotavibs = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    vtotavdifcbs = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    vtotavdevcbs = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    vtotavcbs = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    vtotavcredpresibs = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    vtotavcredpressuspibs = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    vtotavcredprescbs = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    vtotavcredpressuspcbs = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    vtotaadremibsret = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)
    vtotaadremcbsret = models.DecimalField(max_digits=13, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'nfevv'
        unique_together = (('empresa', 'filial', 'b06_mod', 'b07_serie', 'b08_nnf'),)



class Infvv(models.Model):
    id = models.IntegerField(primary_key=True)
    nitem = models.IntegerField()

    i02_cprod = models.CharField(max_length=60, blank=True, null=True)
    i04_xprod = models.CharField(max_length=255, blank=True, null=True)
    i05_ncm = models.CharField(max_length=20, blank=True, null=True)
    i08_cfop = models.CharField(max_length=10, blank=True, null=True)
    i09_ucom = models.CharField(max_length=10, blank=True, null=True)
    i10_qcom = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    i10a_vuncom = models.DecimalField(max_digits=15, decimal_places=6, blank=True, null=True)
    i11_vprod = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    i17_vdesc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    n12_cst = models.CharField(max_length=4, blank=True, null=True)
    n15_vbc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    n16_picms = models.DecimalField(max_digits=7, decimal_places=4, blank=True, null=True)
    n17_vicms = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    n21_vbcst = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    n23_vicmsst = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    o14_vipi = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    q06_cst_pis = models.CharField(max_length=4, blank=True, null=True)
    q07_vbc_pis = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    q08_ppis = models.DecimalField(max_digits=7, decimal_places=4, blank=True, null=True)
    q09_vpis = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    s06_cst_cofins = models.CharField(max_length=4, blank=True, null=True)
    s07_vbc_cofins = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    s08_pcofins = models.DecimalField(max_digits=7, decimal_places=4, blank=True, null=True)
    s11_vcofins = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "infvv"
        unique_together = (("id", "nitem"),)


class NotaFiscal(models.Model):
    empresa = models.IntegerField()
    filial = models.IntegerField()

    modelo = models.CharField(max_length=2, blank=True, null=True)
    serie = models.CharField(max_length=3, blank=True, null=True)
    numero = models.IntegerField(blank=True, null=True)

    data_emissao = models.DateField(blank=True, null=True)
    data_saida = models.DateField(blank=True, null=True)

    tipo_operacao = models.IntegerField(blank=True, null=True)

    emitente = models.ForeignKey(Filial, on_delete=models.PROTECT, db_constraint=False)
    destinatario = models.ForeignKey(Entidades, on_delete=models.PROTECT, db_constraint=False)

    status = models.IntegerField(blank=True, null=True)
    chave_acesso = models.CharField(max_length=50, blank=True, null=True)
    protocolo_autorizacao = models.CharField(max_length=60, blank=True, null=True)

    class Meta:
        db_table = "nf_nota"
        managed = False


class NotaFiscalItem(models.Model):
    nota = models.ForeignKey(NotaFiscal, related_name="itens", on_delete=models.CASCADE)
    produto = models.ForeignKey(Produtos, on_delete=models.PROTECT, db_constraint=False)

    quantidade = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    unitario = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    desconto = models.DecimalField(max_digits=15, decimal_places=4, default=0)

    cfop = models.CharField(max_length=4, blank=True, null=True)
    ncm = models.CharField(max_length=8, blank=True, null=True)
    cest = models.CharField(max_length=7, blank=True, null=True)

    cst_icms = models.CharField(max_length=3, blank=True, null=True)
    cst_ipi = models.CharField(max_length=3, blank=True, null=True)
    cst_pis = models.CharField(max_length=2, blank=True, null=True)
    cst_cofins = models.CharField(max_length=2, blank=True, null=True)

    total_item = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    valor_frete = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True)
    valor_seguro = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True)
    valor_outras_despesas = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True)

    class Meta:
        db_table = "nf_nota_item"
        managed = False


class NotaFiscalItemImposto(models.Model):
    item = models.OneToOneField(NotaFiscalItem, related_name="impostos", on_delete=models.CASCADE)

    icms_base = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    icms_valor = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    icms_aliquota = models.DecimalField(max_digits=5, decimal_places=2, null=True)

    icms_st_base = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    icms_st_valor = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    icms_st_aliquota = models.DecimalField(max_digits=5, decimal_places=2, null=True)

    ipi_base = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    ipi_aliquota = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    ipi_valor = models.DecimalField(max_digits=15, decimal_places=2, null=True)

    pis_base = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    pis_aliquota = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    pis_valor = models.DecimalField(max_digits=15, decimal_places=2, null=True)

    cofins_base = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    cofins_aliquota = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    cofins_valor = models.DecimalField(max_digits=15, decimal_places=2, null=True)

    class Meta:
        db_table = "nf_item_imposto"
        managed = False


class NotaFiscalTransporte(models.Model):
    nota = models.OneToOneField(NotaFiscal, related_name="transporte", on_delete=models.CASCADE)
    modalidade_frete = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = "nf_transporte"
        managed = False


class SaldoProduto(models.Model):
    produto_codigo = models.OneToOneField(Produtos, on_delete=models.CASCADE, db_column="sapr_prod", primary_key=True)
    empresa = models.CharField(max_length=50, db_column="sapr_empr")
    filial = models.CharField(max_length=50, db_column="sapr_fili")
    saldo_estoque = models.DecimalField(max_digits=10, decimal_places=2, db_column="sapr_sald")

    class Meta:
        db_table = "saldosprodutos"
        managed = False
        unique_together = (("produto_codigo", "empresa", "filial"),)


class ProdutosDetalhados(models.Model):
    codigo = models.CharField(max_length=20, primary_key=True)
    custo = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    empresa = models.CharField(max_length=20, null=True)
    filial = models.CharField(max_length=20, null=True)

    class Meta:
        managed = False
        db_table = "produtos_detalhados"


class EntradaEstoque(models.Model):
    entr_sequ = models.IntegerField(primary_key=True)
    entr_empr = models.IntegerField(default=1)
    entr_fili = models.IntegerField(default=1)
    entr_prod = models.CharField(db_column="entr_prod", max_length=10)
    entr_data = models.DateField(db_column="entr_data")
    entr_quan = models.DecimalField(max_digits=10, decimal_places=2)
    entr_tota = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "entradasestoque"
        managed = False
