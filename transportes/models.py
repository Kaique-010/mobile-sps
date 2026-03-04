from django.db import models


class Veiculos(models.Model):
    
    veic_empr = models.IntegerField(primary_key=True, verbose_name='Empresa')
    veic_tran = models.IntegerField(verbose_name='Transportadora')
    veic_sequ = models.IntegerField(verbose_name='Sequencial')
    veic_espe = models.CharField(max_length=40, blank=True, null=True, verbose_name='Especie')
    veic_marc = models.CharField(max_length=40, blank=True, null=True, verbose_name='Marca')
    veic_frot = models.CharField(max_length=6, blank=True, null=True, verbose_name='Frota')
    veic_aqui = models.DateField(blank=True, null=True, verbose_name='Aquisição')
    veic_ano_fabr = models.CharField(max_length=4, blank=True, null=True, verbose_name='Ano de Fabricação')
    veic_ano_mode = models.CharField(max_length=4, blank=True, null=True, verbose_name='Ano de Modelo')
    veic_cor = models.CharField(max_length=40, blank=True, null=True, verbose_name='Cor')
    veic_tipo = models.CharField(max_length=1, blank=True, null=True, verbose_name='Tipo')
    veic_baix = models.DateField(blank=True, null=True, verbose_name='Baixado')
    veic_moti = models.CharField(max_length=40, blank=True, null=True, verbose_name='Motivo')
    veic_chass = models.CharField(max_length=17, blank=True, null=True, verbose_name='Chassi')
    veic_nume_moto = models.CharField(max_length=40, blank=True, null=True, verbose_name='Número da Moto')
    veic_rena = models.CharField(max_length=11, blank=True, null=True, verbose_name='Renavam')
    veic_rena_expe = models.DateField(blank=True, null=True, verbose_name='Expiração do Renavam')
    veic_nome_segu = models.CharField(max_length=40, blank=True, null=True, verbose_name='Nome do Seguidor')
    veic_venc_segu = models.DateField(blank=True, null=True, verbose_name='Vencimento do Seguidor')
    veic_comb = models.CharField(max_length=1, blank=True, null=True, verbose_name='Combustível')
    veic_plac = models.CharField(max_length=7, blank=True, null=True, verbose_name='Placa')
    veic_cida = models.CharField(max_length=7, blank=True, null=True, verbose_name='Cidade')
    veic_nome_cida = models.CharField(max_length=60, blank=True, null=True, verbose_name='Nome da Cidade')
    veic_esta = models.CharField(max_length=2, blank=True, null=True, verbose_name='Estado')
    veic_valo_aqui = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Valor Aquisição')
    veic_venc_exti = models.DateField(blank=True, null=True, verbose_name='Vencimento Extintor')
    veic_ipva = models.DateField(blank=True, null=True, verbose_name='IPVA')
    veic_segu_obri = models.DateField(blank=True, null=True, verbose_name='Seguidor Obrigatório')
    veic_capa = models.DecimalField(max_digits=15, decimal_places=3, blank=True, null=True, verbose_name='Capacidade')
    veic_adic_km = models.IntegerField(blank=True, null=True, verbose_name='Adicional KM')
    veic_moto = models.IntegerField(blank=True, null=True, verbose_name='Motorista')
    veic_perc_comi = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='Percentual Comissão')
    veic_agre = models.BooleanField(blank=True, null=True, verbose_name='Agregado')
    veic_inic_agre = models.DateField(blank=True, null=True, verbose_name='Início do Agregado')
    veic_fim_agre = models.DateField(blank=True, null=True, verbose_name='Fim do Agregado')
    veic_inat = models.BooleanField(blank=True, null=True, verbose_name='Inativo')
    veic_tara_km = models.DecimalField(max_digits=15, decimal_places=3, blank=True, null=True, verbose_name='Tara KM')
    veic_capa_km = models.DecimalField(max_digits=15, decimal_places=3, blank=True, null=True, verbose_name='Capacidade KM')
    veic_capa_m3 = models.DecimalField(max_digits=15, decimal_places=3, blank=True, null=True, verbose_name='Capacidade M3')
    veic_eixo = models.IntegerField(blank=True, null=True, verbose_name='Eixo')
    veic_impl = models.CharField(max_length=20, blank=True, null=True, verbose_name='Implementação')
    veic_rntr = models.CharField(max_length=8, blank=True, null=True, verbose_name='RNTR')
    veic_prop_veic = models.CharField(max_length=1, blank=True, null=True, verbose_name='Proprietário do Veículo')
    veic_tipo_veic = models.CharField(max_length=1, blank=True, null=True, verbose_name='Tipo de Veículo')
    veic_tipo_roda = models.CharField(max_length=2, blank=True, null=True, verbose_name='Tipo de Roda')
    veic_tipo_carr = models.CharField(max_length=2, blank=True, null=True, verbose_name='Tipo de Carroceria')
    veic_car1 = models.IntegerField(blank=True, null=True, verbose_name='Carroceria 1')
    veic_car2 = models.IntegerField(blank=True, null=True, verbose_name='Carroceria 2')
    veic_car3 = models.IntegerField(blank=True, null=True, verbose_name='Carroceria 3')
    veic_car4 = models.IntegerField(blank=True, null=True, verbose_name='Carroceria 4')
    veic_tipo_prop = models.CharField(max_length=1, blank=True, null=True, verbose_name='Tipo de Proprietário')
    veic_fili_patr = models.IntegerField(blank=True, null=True, verbose_name='Filial da Proprietária')
    veic_codi_patr = models.CharField(max_length=13, blank=True, null=True, verbose_name='Código da Proprietária')
    veic_moni = models.CharField(max_length=40, blank=True, null=True, verbose_name='Monitor')
    veic_nume_rast = models.CharField(max_length=40, blank=True, null=True, verbose_name='Número de Rastreio')
    veic_obse = models.TextField(blank=True, null=True, verbose_name='Observações')
    veic_cecu = models.IntegerField(blank=True, null=True, verbose_name='Código do CC')

    class Meta:
        managed = False
        db_table = 'veiculos'
        unique_together = (('veic_empr', 'veic_tran', 'veic_sequ'),)
        



class Cte(models.Model):
    
    #dados da emissao do cte
    id = models.CharField(max_length=50, blank=True, primary_key=True, db_column='cte_id')
    empresa = models.IntegerField(db_column='cte_empr')
    filial = models.IntegerField(db_column='cte_fili')
    modelo = models.CharField(max_length=2, db_column='cte_mode')
    serie = models.CharField(max_length=3, db_column='cte_seri')
    subserie = models.CharField(max_length=3, db_column='cte_suse')
    numero = models.DecimalField(max_digits=9, decimal_places=0, db_column='cte_nume')
    emissao = models.DateField(blank=True, null=True, db_column='cte_emis')
    hora = models.TimeField(blank=True, null=True, db_column='cte_hora')
    remetente = models.IntegerField(blank=True, null=True, db_column='cte_reme')
    destinatario = models.IntegerField(blank=True, null=True, db_column='cte_dest')
    motorista = models.IntegerField(blank=True, null=True, db_column='cte_moto')
    veiculo = models.IntegerField(blank=True, null=True, db_column='cte_veic')
    placa1 = models.CharField(max_length=7, blank=True, null=True, db_column='cte_pla1')
    placa2 = models.CharField(max_length=7, blank=True, null=True, db_column='cte_pla2')
    placa3 = models.CharField(max_length=7, blank=True, null=True, db_column='cte_pla3')
    placa4 = models.CharField(max_length=7, blank=True, null=True, db_column='cte_pla4')
    
    
    #tipos e formas de emissão
    tomador_servico = models.IntegerField(blank=True, null=True, db_column='cte_toma_serv', choices=[(1, 'Remetente'),
                                                                                                     (2, 'Expedidor'),
                                                                                                     (3, 'Recebedor'),
                                                                                                     (4, 'Destinatário'),
                                                                                                     (5, 'Outros')])
    tipo_servico = models.IntegerField(blank=True, null=True, db_column='cte_tipo_serv', choices=[(1, '1 - Normal'),
                                                                                                     (2, '2 - Sub-Contratado'),
                                                                                                     (3, '3 - Redespacho'),
                                                                                                     (4, '4 - Redespacho Intermediário')])
    tipo_cte = models.IntegerField(blank=True, null=True, db_column='cte_tipo_cte', choices=[(1, 'Normal'),
                                                                                              (2, 'Complemento'),
                                                                                              (3, 'Anulação'),
                                                                                              (4, 'Substituto')])
    forma_emissao = models.IntegerField(blank=True, null=True, db_column='cte_form_emis', choices=[(1, '1 - Normal'),
                                                                                                     (2, '2 - Contingência'),])
    tipo_frete = models.IntegerField(blank=True, null=True, db_column='cte_tipo_fret', choices=[(1, '1 - Por Conta do Emitente'),
                                                                                                (2, '2 - Por Conta do Destinatário'),
                                                                                                (3, '3 - Por Conta de Terceiros'), 
                                                                                                (4, '4 - Sem Cobrança')])
    redespacho = models.IntegerField(blank=True, null=True, db_column='cte_rede')
    subcontratado = models.IntegerField(blank=True, null=True, db_column='cte_suco')
    outro_tomador = models.IntegerField(blank=True, null=True, db_column='cte_outr_toma')
    transportadora = models.IntegerField(blank=True, null=True, db_column='cte_tran')
    
    
    #Informaçoes para a rota do cte
    cidade_coleta = models.IntegerField(blank=True, null=True, db_column='cte_cole')
    cidade_entrega = models.IntegerField(blank=True, null=True, db_column='cte_entr')
    pedagio = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_peda')
    peso_total = models.DecimalField(max_digits=15, decimal_places=3, blank=True, null=True, db_column='cte_peso_tota')
    tarifa = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_tari')
    frete_peso = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_fret_peso')
    frete_valor = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_fret_valo')
    outras_observacoes = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_outr')
    
    
    #campos para o seguro do cte
    seguro_por_conta = models.IntegerField(blank=True, null=True, db_column='cte_segu_porc', choices=[(1, 'Remetente'), (2, 'Destinatário'), (3, 'Emitente'), (4, 'Tomador')])
    seguradora = models.IntegerField(blank=True, null=True, db_column='cte_segu')
    valor_base_seguro = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_base_segu')
    numero_apolice = models.CharField(max_length=40, blank=True, null=True, db_column='cte_nume_apol')
    numero_averbado = models.CharField(max_length=40, blank=True, null=True, db_column='cte_nume_aver')
    percentual_seguro = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_perc_segu')
    cte_valor_seguro = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_valo_segu')
    observacoes = models.TextField(blank=True, null=True, db_column='cte_obse_cont')
    observacoes_fiscais = models.TextField(blank=True, null=True, db_column='cte_obse_fisc')
    

   #Tarifas e valores a pagar sobre o frete cte
    tarifa_motorista = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_tari_moto')
    frete_motorista = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_fret_moto')
    total_valor = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_tota_valo')
    vale_pedagio = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_vale_peda')
    
    
    #Valores a receber
    liquido_a_receber = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_liqu_rece')
    vencimento = models.DateField(blank=True, null=True, db_column='cte_venc')
    
    
    #Informações sobre a carga transportada 
    total_mercadoria = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_tota_merc')
    produto_predominante = models.CharField(max_length=100, blank=True, null=True, db_column='cte_prod_pred')
    unidade_medida = models.CharField(max_length=2, blank=True, null=True, db_column='cte_unid_medi')
    tipo_medida = models.CharField(max_length=100, blank=True, null=True, db_column='cte_tipo_medi', choices=[('KG', 'KG'), ('UN', 'UN'), ('MT', 'MT'), ('CM', 'CM'), ('LITRO', 'LITRO'), ('TN', 'TONELADA')])
    numero_contrato = models.CharField(max_length=20, blank=True, null=True, db_column='cte_nume_cont')
    numero_lacre = models.CharField(max_length=20, blank=True, null=True, db_column='cte_nume_lacr')
    data_previsao_entrega = models.DateField(blank=True, null=True, db_column='cte_data_prev')
    ncm = models.CharField(max_length=10, blank=True, null=True, db_column='cte_ncm')
    total_peso = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, db_column='cte_tota_peso')
    frotador = models.BooleanField(blank=True, null=True, db_column='cte_frot')
    numero_lote = models.IntegerField(blank=True, null=True, db_column='cte_cafr_nume')
    mdf = models.IntegerField(blank=True, null=True, db_column='mdf')
    data_chegada = models.DateField(blank=True, null=True, db_column='cte_data_cheg')
    hora_chegada = models.TimeField(blank=True, null=True, db_column='cte_hora_cheg')
    km_chegada = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_km_cheg')
    diferenca_km = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_dife_km')
    peso_chegada = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, db_column='cte_peso_cheg')
    diferenca_peso = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, db_column='cte_dife_peso')
    observacao_chegada = models.TextField(blank=True, null=True, db_column='cte_obse_cheg')
    chave_de_acesso = models.CharField(max_length=44, blank=True, null=True, db_column='cte_doc_chav')
    cnpj = models.CharField(max_length=14, blank=True, null=True, db_column='cte_doc_cnpj')
    ie = models.CharField(max_length=20, blank=True, null=True, db_column='cte_doc_ie')
    estado = models.CharField(max_length=2, blank=True, null=True, db_column='cte_doc_esta')
    consolidadado_final = models.BooleanField(blank=True, null=True, db_column='cte_cons_fina')
    
    #Campos Fiscais  do frete
    usuario = models.IntegerField(blank=True, null=True, db_column='cte_usua')
    xml_cte = models.TextField(blank=True, null=True, db_column='cte_xml_cte')
    xml_canc = models.TextField(blank=True, null=True, db_column='cte_xml_canc')
    xml_inut = models.TextField(blank=True, null=True, db_column='cte_xml_inut')
    status = models.CharField(max_length=3, blank=True, null=True, db_column='cte_stat')
    protocolo = models.CharField(max_length=50, blank=True, null=True, db_column='cte_prot_cte')
    protocolo_cancelamento = models.CharField(max_length=50, blank=True, null=True, db_column='cte_prot_canc')
    protocolo_inutilizacao = models.CharField(max_length=50, blank=True, null=True, db_column='cte_prot_inut')
    cte_referencia = models.CharField(max_length=50, blank=True, null=True, db_column='cte_cte_refe')
    data_anulacao = models.DateField(blank=True, null=True, db_column='cte_data_anul')
    cancelado = models.BooleanField(blank=True, null=True, db_column='cte_canc')
    inutilizado = models.BooleanField(blank=True, null=True, db_column='cte_inut')
    denegado = models.BooleanField(blank=True, null=True, db_column='cte_dene')
    lote = models.IntegerField(blank=True, null=True, db_column='cte_lote')
    
    
    
    #dados para tributação do cte
    cfop = models.IntegerField(blank=True, null=True, db_column='cte_cfop')
    cst_icms = models.CharField(max_length=3, blank=True, null=True, db_column='cte_cst_icms')
    aliq_icms = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_aliq_icms')
    base_icms = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_base_icms')
    reducao_icms = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_redu_icms')
    valor_icms = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_valo_icms')
    total_valor_liquido = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_tota_ctrc')
    isencao_icms = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_isen_icms')
    valor_outros_icms = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_voutr_icms')
    diferenca_icms = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_dife_icms')
    cst_pis = models.CharField(max_length=2, blank=True, null=True, db_column='cte_cst_pis')
    aliquota_pis = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_aliq_pis')
    base_pis = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_base_pis')
    valor_pis = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_valo_pis')
    cst_cofins = models.CharField(max_length=2, blank=True, null=True, db_column='cte_cst_cofi')
    aliquota_cofins = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_aliq_cofi')
    base_cofins = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_base_cofi')
    valor_cofins = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_valo_cofi')
    ibscbs_vbc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_ibscbs_vbc')
    ibscbs_cstid = models.IntegerField(blank=True, null=True, db_column='cte_ibscbs_cstid')
    ibscbs_cst = models.CharField(max_length=3, blank=True, null=True, db_column='cte_ibscbs_cst')
    ibscbs_cclasstrib = models.CharField(max_length=6, blank=True, null=True, db_column='cte_ibscbs_cclasstrib')
    ibs_pdifuf = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_ibs_pdifuf')
    ibs_vdifuf = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_ibs_vdifuf')
    ibs_vdevtribuf = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_ibs_vdevtribuf')
    ibs_vdevtribmun = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_ibs_vdevtribmun')
    cbs_vdevtrib = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_cbs_vdevtrib')
    ibs_pibsuf = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_ibs_pibsuf')
    ibs_preduf = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_ibs_preduf')
    ibs_paliqefetuf = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_ibs_paliqefetuf')
    ibs_vibsuf = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_ibs_vibsuf')
    ibs_pdifmun = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_ibs_pdifmun')
    ibs_vdifmun = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_ibs_vdifmun')
    ibs_pibsmun = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_ibs_pibsmun')
    ibs_predmun = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_ibs_predmun')
    ibs_paliqefetmun = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_ibs_paliqefetmun')
    ibs_vibsmun = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_ibs_vibsmun')
    ibs_vibs = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_ibs_vibs')
    cbs_pdif = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_cbs_pdif')
    cbs_vdif = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_cbs_vdif')
    cbs_pcbs = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_cbs_pcbs')
    cbs_pred = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_cbs_pred')
    cbs_paliqefet = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_cbs_paliqefet')
    cbs_vcbs = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_cbs_vcbs')
    ibscbs_cstregid = models.IntegerField(blank=True, null=True, db_column='cte_ibscbs_cstregid')
    ibscbs_cstreg = models.CharField(max_length=3, blank=True, null=True, db_column='cte_ibscbs_cstreg')
    ibscbs_cclasstribreg = models.CharField(max_length=6, blank=True, null=True, db_column='cte_ibscbs_cclasstribreg')
    ibs_paliqefetufreg = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_ibs_paliqefetufreg')
    ibs_vtribufreg = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_ibs_vtribufreg')

    class Meta:
        managed = False
        db_table = 'cte'


class CteDocumento(models.Model):
    id = models.AutoField(primary_key=True)
    cte = models.ForeignKey(Cte, on_delete=models.CASCADE, db_column='ctdo_cte_id', related_name='documentos', db_constraint=False)
    chave_nfe = models.CharField(max_length=44, blank=True, null=True, db_column='ctdo_chav_nfe', verbose_name='Chave NFe')
    tipo_doc = models.CharField(max_length=2, default='00', db_column='ctdo_tipo', verbose_name='Tipo Documento') # 00=NFe

    class Meta:
        managed = True
        db_table = 'cte_documento'
