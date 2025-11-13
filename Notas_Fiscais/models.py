from django.db import models

class NotaFiscal(models.Model):
    # --- Bloco B: Identificação da NF-e ---
    # Estes são os campos de identificação geral da nota fiscal.
    codigo_uf_emitente = models.IntegerField(db_column='b02_cuf_emi', blank=True, null=True, help_text="Código da UF do emitente do Documento Fiscal")
    codigo_numerico_chave = models.IntegerField(db_column='b03_cnf', blank=True, null=True, help_text="Código Numérico que compõe a Chave de Acesso")
    natureza_operacao = models.CharField(db_column='b04_natop', max_length=60, blank=True, null=True, help_text="Descrição da Natureza da Operação")
    modelo = models.CharField(db_column='b06_mod', max_length=2, blank=True, null=True, help_text="Código do modelo do Documento Fiscal")
    serie = models.CharField(db_column='b07_serie', max_length=3, blank=True, null=True, help_text="Série do Documento Fiscal")
    numero_nota_fiscal = models.IntegerField(db_column='b08_nnf', blank=True, null=True, help_text="Número do Documento Fiscal")
    data_emissao = models.DateField(db_column='b09_demi', blank=True, null=True, help_text="Data de emissão do Documento Fiscal")
    data_saida_entrada = models.DateField(db_column='b10_dsaient', blank=True, null=True, help_text="Data de Saída ou da Entrada da Mercadoria/Produto")
    hora_saida_entrada = models.TimeField(db_column='b10a_hsaient', blank=True, null=True, help_text="Hora de Saída ou da Entrada da Mercadoria/Produto")
    tipo_operacao = models.IntegerField(db_column='b11_tpnf', blank=True, null=True, help_text="Tipo de Operação (0-entrada; 1-saída)")
    id_local_destino = models.IntegerField(db_column='nfev_id_dest', blank=True, null=True, help_text="Identificador de local de destino da operação (1-Interna; 2-Interestadual; 3-Exterior)")
    codigo_municipio_fg = models.IntegerField(db_column='b12_cmunfg', blank=True, null=True, help_text="Código do Município de Ocorrência do Fato Gerador")
    
    # --- Configurações de Emissão ---
    tipo_impressao_danfe = models.IntegerField(db_column='b21_tplmp', blank=True, null=True, help_text="Formato de Impressão do DANFE")
    tipo_emissao = models.IntegerField(db_column='b22_tpemis', blank=True, null=True, help_text="Forma de emissão da NF-e")
    digito_verificador_chave = models.IntegerField(db_column='b23_cdv', blank=True, null=True, help_text="Dígito Verificador da Chave de Acesso da NF-e")
    ambiente = models.IntegerField(db_column='b24_tpamb', blank=True, null=True, help_text="Identificação do Ambiente (1-Produção; 2-Homologação)")
    finalidade_emissao = models.IntegerField(db_column='b25_finnfe', blank=True, null=True, help_text="Finalidade de emissão da NF-e")
    consumidor_final = models.IntegerField(db_column='b25a_indfinal', blank=True, null=True, help_text="Indica operação com Consumidor final")
    indicador_presenca = models.IntegerField(db_column='b25b_indpres', blank=True, null=True, help_text="Indicador de presença do comprador no estabelecimento")
    processo_emissao = models.IntegerField(db_column='b26_procemi', blank=True, null=True, help_text="Processo de emissão da NF-e")
    versao_processo = models.CharField(db_column='b27_verproc', max_length=20, blank=True, null=True, help_text="Versão do Processo de emissão da NF-e")
    data_hora_contingencia = models.CharField(db_column='b28_dhcont', max_length=25, blank=True, null=True, help_text="Data e Hora da entrada em contingência") # Ajustado para CharField para acomodar data e hora
    justificativa_contingencia = models.TextField(db_column='b29_xjust', blank=True, null=True, help_text="Justificativa da entrada em contingência")

    # --- A. Dados da NF-e (Chave e Versão) ---
    versao_layout = models.DecimalField(db_column='a02_versao', max_digits=4, decimal_places=2, blank=True, null=True, help_text="Versão do leiaute da NF-e")
    chave_acesso = models.CharField(db_column='a03_id', max_length=47, blank=True, null=True, help_text="Chave de acesso da NF-e (sem o 'NFe' inicial)")

    # --- C. Emitente ---
    emitente_cnpj = models.CharField(db_column='c02_cnpj', max_length=14, blank=True, null=True)
    emitente_cpf = models.CharField(db_column='c02a_cpf', max_length=11, blank=True, null=True)
    emitente_razao_social = models.CharField(db_column='c03_xnome', max_length=60, blank=True, null=True)
    emitente_nome_fantasia = models.CharField(db_column='c04_xfant', max_length=60, blank=True, null=True)
    emitente_logradouro = models.CharField(db_column='c06_xlgr', max_length=60, blank=True, null=True)
    emitente_numero = models.CharField(db_column='c07_nro', max_length=60, blank=True, null=True)
    emitente_complemento = models.CharField(db_column='c08_xcpl', max_length=60, blank=True, null=True)
    emitente_bairro = models.CharField(db_column='c09_xbairro', max_length=60, blank=True, null=True)
    emitente_codigo_municipio = models.IntegerField(db_column='c10_cmun', blank=True, null=True)
    emitente_nome_municipio = models.CharField(db_column='c11_xmun', max_length=60, blank=True, null=True)
    emitente_uf = models.CharField(db_column='c12_uf', max_length=2, blank=True, null=True)
    emitente_cep = models.IntegerField(db_column='c13_cep', blank=True, null=True)
    emitente_codigo_pais = models.IntegerField(db_column='c14_cpais', blank=True, null=True)
    emitente_nome_pais = models.CharField(db_column='c15_xpais', max_length=60, blank=True, null=True)
    emitente_fone = models.CharField(db_column='c16_fone', max_length=15, blank=True, null=True)
    emitente_ie = models.CharField(db_column='c17_ie', max_length=14, blank=True, null=True, help_text="Inscrição Estadual")
    emitente_ie_st = models.CharField(db_column='c18_iest', max_length=14, blank=True, null=True, help_text="IE do Substituto Tributário")
    emitente_im = models.CharField(db_column='c19_im', max_length=15, blank=True, null=True, help_text="Inscrição Municipal")
    emitente_cnae = models.CharField(db_column='c20_cnae', max_length=7, blank=True, null=True, help_text="CNAE fiscal")
    emitente_crt = models.IntegerField(db_column='c21_crt', blank=True, null=True, help_text="Código de Regime Tributário")
    
    # --- E. Destinatário ---
    destinatario_cnpj = models.CharField(db_column='e02_cnpj', max_length=14, blank=True, null=True)
    destinatario_cpf = models.CharField(db_column='e03_cpf', max_length=11, blank=True, null=True)
    destinatario_razao_social = models.CharField(db_column='e04_xnome', max_length=60, blank=True, null=True)
    destinatario_logradouro = models.CharField(db_column='e06_xlgr', max_length=60, blank=True, null=True)
    destinatario_numero = models.CharField(db_column='e07_nro', max_length=60, blank=True, null=True)
    destinatario_complemento = models.CharField(db_column='e08_xcpl', max_length=60, blank=True, null=True)
    destinatario_bairro = models.CharField(db_column='e09_xbairro', max_length=60, blank=True, null=True)
    destinatario_codigo_municipio = models.IntegerField(db_column='e10_cmun', blank=True, null=True)
    destinatario_nome_municipio = models.CharField(db_column='e11_xmun', max_length=60, blank=True, null=True)
    destinatario_uf = models.CharField(db_column='e12_uf', max_length=2, blank=True, null=True)
    destinatario_cep = models.IntegerField(db_column='e13_cep', blank=True, null=True)
    destinatario_codigo_pais = models.IntegerField(db_column='e14_cpais', blank=True, null=True)
    destinatario_nome_pais = models.CharField(db_column='e15_xpais', max_length=60, blank=True, null=True)
    destinatario_fone = models.CharField(db_column='e16_fone', max_length=15, blank=True, null=True)
    destinatario_ie = models.CharField(db_column='e17_ie', max_length=14, blank=True, null=True, help_text="Inscrição Estadual")
    destinatario_isuf = models.CharField(db_column='e18_isuf', max_length=9, blank=True, null=True, help_text="Inscrição SUFRAMA")
    destinatario_email = models.CharField(db_column='e19_email', max_length=60, blank=True, null=True)

    # --- F. Local de Retirada ---
    retirada_cnpj = models.CharField(db_column='f02_cnpj', max_length=14, blank=True, null=True)
    retirada_cpf = models.CharField(db_column='f02a_cpf', max_length=11, blank=True, null=True)
    retirada_logradouro = models.CharField(db_column='f03_xlgr', max_length=60, blank=True, null=True)
    retirada_numero = models.CharField(db_column='f04_nro', max_length=60, blank=True, null=True)
    retirada_complemento = models.CharField(db_column='f05_xcpl', max_length=60, blank=True, null=True)
    retirada_bairro = models.CharField(db_column='f06_xbairro', max_length=60, blank=True, null=True)
    retirada_codigo_municipio = models.IntegerField(db_column='f07_cmun', blank=True, null=True)
    retirada_nome_municipio = models.CharField(db_column='f08_xmun', max_length=60, blank=True, null=True)
    retirada_uf = models.CharField(db_column='f09_uf', max_length=2, blank=True, null=True)

    # --- G. Local de Entrega ---
    entrega_cnpj = models.CharField(db_column='g02_cnpj', max_length=14, blank=True, null=True)
    entrega_cpf = models.CharField(db_column='g02a_cpf', max_length=11, blank=True, null=True)
    entrega_logradouro = models.CharField(db_column='g03_xlgr', max_length=60, blank=True, null=True)
    entrega_numero = models.CharField(db_column='g04_nro', max_length=60, blank=True, null=True)
    entrega_complemento = models.CharField(db_column='g05_xcpl', max_length=60, blank=True, null=True)
    entrega_bairro = models.CharField(db_column='g06_xbarirro', max_length=60, blank=True, null=True) # Note: 'xbarirro' no nome da coluna original
    entrega_codigo_municipio = models.IntegerField(db_column='g07_cmun', blank=True, null=True)
    entrega_nome_municipio = models.CharField(db_column='g08_xmun', max_length=60, blank=True, null=True)
    entrega_uf = models.CharField(db_column='g09_uf', max_length=2, blank=True, null=True)

    # --- W. Totais da NF-e ---
    valor_total_bc_icms = models.DecimalField(db_column='w03_vbc_tota', max_digits=15, decimal_places=2, blank=True, null=True)
    valor_total_icms = models.DecimalField(db_column='w04_vicms_tota', max_digits=15, decimal_places=2, blank=True, null=True)
    valor_total_icms_desonerado = models.DecimalField(db_column='vicmsdeson', max_digits=15, decimal_places=2, blank=True, null=True)
    valor_total_bc_icms_st = models.DecimalField(db_column='w05_vbcst_tota', max_digits=15, decimal_places=2, blank=True, null=True)
    valor_total_icms_st = models.DecimalField(db_column='w06_vst_tota', max_digits=15, decimal_places=2, blank=True, null=True)
    valor_total_produtos = models.DecimalField(db_column='w07_vprod_tota', max_digits=15, decimal_places=2, blank=True, null=True)
    valor_total_frete = models.DecimalField(db_column='w08_vfret_tota', max_digits=15, decimal_places=2, blank=True, null=True)
    valor_total_seguro = models.DecimalField(db_column='w09_vseg_tota', max_digits=15, decimal_places=2, blank=True, null=True)
    valor_total_desconto = models.DecimalField(db_column='w10_vdesc_tota', max_digits=15, decimal_places=2, blank=True, null=True)
    valor_total_ii = models.DecimalField(db_column='w11_vii_tota', max_digits=15, decimal_places=2, blank=True, null=True, help_text="Imposto de Importação")
    valor_total_ipi = models.DecimalField(db_column='w12_vipi_tota', max_digits=15, decimal_places=2, blank=True, null=True)
    valor_total_pis = models.DecimalField(db_column='w13_vpis_tota', max_digits=15, decimal_places=2, blank=True, null=True)
    valor_total_cofins = models.DecimalField(db_column='w14_vcofins_tota', max_digits=15, decimal_places=2, blank=True, null=True)
    valor_total_outras_despesas = models.DecimalField(db_column='w15_voutro_tota', max_digits=15, decimal_places=2, blank=True, null=True)
    valor_total_nota = models.DecimalField(db_column='w16_vnf_tota', max_digits=15, decimal_places=2, blank=True, null=True)
    valor_total_tributos = models.DecimalField(db_column='vtottrib', max_digits=15, decimal_places=2, blank=True, null=True)
    
    # --- X. Transporte ---
    modalidade_frete = models.IntegerField(db_column='x02_modfrete', blank=True, null=True)
    transportador_cnpj = models.CharField(db_column='x04_cnpj_transp', max_length=14, blank=True, null=True)
    transportador_cpf = models.CharField(db_column='x05_cpf_transp', max_length=11, blank=True, null=True)
    transportador_razao_social = models.CharField(db_column='x06_xnome_transp', max_length=60, blank=True, null=True)
    transportador_ie = models.CharField(db_column='x07_ie_transp', max_length=14, blank=True, null=True)
    transportador_endereco = models.CharField(db_column='x08_xender_transp', max_length=60, blank=True, null=True)
    transportador_nome_municipio = models.CharField(db_column='x09_xmun_transp', max_length=60, blank=True, null=True)
    transportador_uf = models.CharField(db_column='x10_uf_transp', max_length=2, blank=True, null=True)
    veiculo_placa = models.CharField(db_column='x19_placa_veic', max_length=8, blank=True, null=True)
    veiculo_uf = models.CharField(db_column='x20_uf_veic', max_length=2, blank=True, null=True)
    veiculo_rntc = models.CharField(db_column='x21_rntc_veic', max_length=20, blank=True, null=True, help_text="Registro Nacional de Transportador de Carga")
    # ... outros campos de reboque e transporte podem ser adicionados aqui se necessário

    # --- Campos de Controle do Sistema ---
    empresa = models.IntegerField(blank=True, null=True)
    filial = models.IntegerField(blank=True, null=True)
    cliente = models.IntegerField(blank=True, null=True) 
    vendedor = models.IntegerField(blank=True, null=True)
    transportadora = models.IntegerField(blank=True, null=True) 
    usuario = models.IntegerField(blank=True, null=True)
    
    # --- Status e XMLs ---
    xml_nfe = models.TextField(blank=True, null=True)
    protocolo_nfe = models.CharField(db_column='prot_nfe', max_length=50, blank=True, null=True)
    status_nfe = models.IntegerField(blank=True, null=True)
    cancelada = models.BooleanField(blank=True, null=True)
    xml_cancelamento = models.TextField(db_column='xml_canc', blank=True, null=True)
    protocolo_cancelamento = models.CharField(db_column='prot_canc', max_length=50, blank=True, null=True)
    status_cancelamento = models.IntegerField(db_column='status_canc', blank=True, null=True)
    inutilizada = models.BooleanField(blank=True, null=True)
    xml_inutilizacao = models.TextField(db_column='xml_inut', blank=True, null=True)
    status_inutilizacao = models.IntegerField(db_column='status_inut', blank=True, null=True)
    denegada = models.BooleanField(blank=True, null=True)
    troco = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    # --- Log (Campos com _ no início foram ajustados) ---
    log_data = models.DateField(db_column='_log_data', blank=True, null=True)
    log_hora = models.TimeField(db_column='_log_time', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'nfevv'
        verbose_name = "Nota Fiscal"
        verbose_name_plural = "Notas Fiscais"
        unique_together = (('empresa', 'filial', 'modelo', 'serie', 'numero_nota_fiscal'),)
