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
        

class MotoristasCadastros(models.Model):
    STATUS_CHOICES = (
        ('ATV', 'Ativo'),
        ('INA', 'Inativo'),
        ('BLO', 'Bloqueado'),
    )

    id = models.AutoField(primary_key=True)
    empresa = models.IntegerField(db_column='moto_empr')
    filial = models.IntegerField(db_column='moto_fili')
    entidade = models.IntegerField(db_column='moto_enti')
    status = models.CharField(
        max_length=3,
        db_column='moto_stat',
        choices=STATUS_CHOICES,
        default='ATV'
    )
    criado_em = models.DateTimeField(db_column='moto_cria_em', auto_now_add=True)
    atualizado_em = models.DateTimeField(db_column='moto_atual_em', auto_now=True)

    class Meta:
        db_table = 'motoristas'
        ordering = ('-criado_em',)
        unique_together = ('empresa', 'filial', 'entidade')

    def __str__(self):
        return f"Motorista {self.entidade} ({self.get_status_display()})"

    @property
    def ativo(self):
        return self.status == 'ATV'

class MotoristaDocumento(models.Model):
    STATUS_CHOICES = (
        ('pendente', 'Pendente'),
        ('valido', 'Válido'),
        ('vencendo', 'Vencendo'),
        ('vencido', 'Vencido'),
    )

    id = models.AutoField(primary_key=True, db_column='moto_docu_id')
    tipo_doc = models.CharField(max_length=30, db_column='moto_tipo_doc')
    empresa = models.IntegerField(db_column='moto_empr')
    filial = models.IntegerField(db_column='moto_fili')
    entidade = models.IntegerField(db_column='moto_enti')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendente',
        db_column='moto_stat'
    )
    numero = models.CharField(max_length=50, blank=True, null=True, db_column='moto_nume')
    data_emissao = models.DateField(blank=True, null=True, db_column='moto_data_emis')
    data_validade = models.DateField(blank=True, null=True, db_column='moto_data_val')
    criado_em = models.DateTimeField(db_column='moto_cria_em', auto_now_add=True)
    atualizado_em = models.DateTimeField(db_column='moto_atual_em', auto_now=True)
    alerta_em_dias = models.IntegerField(db_column='moto_alerta_dias', default=30)
    observacoes = models.TextField(blank=True, null=True, db_column='moto_obse')
    anexos = models.TextField(blank=True, null=True, db_column='moto_anexos')

    class Meta:
        db_table = 'motoristas_documentos'
        ordering = ('-criado_em',)

    def __str__(self):
        return f"{self.tipo_doc} - {self.entidade}"


class TipoDocumentoMotorista(models.Model):
    id = models.AutoField(primary_key=True)
    descricao = models.CharField(max_length=100, db_column='tdoc_desc')
    slug = models.CharField(max_length=30, unique=True, db_column='tdoc_slug')
    exige_validade = models.BooleanField(default=True, db_column='tdoc_exige_val')
    alerta_padrao_dias = models.IntegerField(default=30, db_column='tdoc_alerta')
    ativo = models.BooleanField(default=True, db_column='tdoc_ativo')

    class Meta:
        db_table = 'tipos_documentos_motoristas'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao


class MotoristaDadosComplementares(models.Model):
    id = models.AutoField(primary_key=True, db_column='mdad_id')
    empresa = models.IntegerField(db_column='mdad_empr')
    filial = models.IntegerField(db_column='mdad_fili')
    entidade = models.IntegerField(db_column='mdad_enti')
    cnh_numero = models.CharField(max_length=20, blank=True, null=True, db_column='mdad_cnh')
    cnh_categoria = models.CharField(max_length=5, blank=True, null=True, db_column='mdad_cnh_cat')
    cnh_validade = models.DateField(blank=True, null=True, db_column='mdad_cnh_val')
    rg_numero = models.CharField(max_length=20, blank=True, null=True, db_column='mdad_rg')
    ear = models.BooleanField(default=False, db_column='mdad_ear')
    ear_validade = models.DateField(blank=True, null=True, db_column='mdad_ear_val')
    criado_em = models.DateTimeField(db_column='mdad_cria_em', auto_now_add=True)
    atualizado_em = models.DateTimeField(db_column='mdad_atual_em', auto_now=True)

    class Meta:
        db_table = 'motoristas_dados_complementares'
        ordering = ('-criado_em',)
        unique_together = ('empresa', 'filial', 'entidade')

    def __str__(self):
        return f"Dados motorista {self.entidade}"

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
    recibo = models.CharField(max_length=50, blank=True, null=True, db_column='cte_reci')
    
    @property
    def chave(self):
        return self.chave_de_acesso

    cnpj = models.CharField(max_length=14, blank=True, null=True, db_column='cte_doc_cnpj')
    ie = models.CharField(max_length=20, blank=True, null=True, db_column='cte_doc_ie')
    estado = models.CharField(max_length=2, blank=True, null=True, db_column='cte_doc_esta')
    consolidadado_final = models.BooleanField(blank=True, null=True, db_column='cte_cons_fina')
    
    #Campos Fiscais  do frete
    usuario = models.IntegerField(blank=True, null=True, db_column='cte_usua')
    xml_cte = models.TextField(blank=True, null=True, db_column='cte_xml_cte')
    xml_canc = models.TextField(blank=True, null=True, db_column='cte_xml_canc')
    xml_inut = models.TextField(blank=True, null=True, db_column='cte_xml_inut')
    
    STATUS_CTE_CHOICES = [
        ('RAS', 'Rascunho'),
        ('AUT', 'Autorizado'),
        ('REJ', 'Rejeitado'),
        ('REC', 'Recebido'),
        ('CAN', 'Cancelado'),
        ('INU', 'Inutilizado'),
        ('ERR', 'Erro'),
        ('PRO', 'Processando'),
    ]
    status = models.CharField(max_length=3, blank=True, null=True, db_column='cte_stat', choices=STATUS_CTE_CHOICES)
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
    
    # Campos ST (Substituição Tributária) - Adicionados para compatibilidade com Services
    base_icms_st = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_base_st')
    aliquota_icms_st = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_aliq_st')
    valor_icms_st = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_valo_st')
    margem_valor_adicionado_st = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_mva_st')
    reducao_base_icms_st = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_redu_st')

    # Campos DIFAL (Partilha) - Adicionados para compatibilidade com Services
    valor_bc_uf_dest = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_vbc_uf_dest')
    valor_icms_uf_dest = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, db_column='cte_vicms_uf_dest')
    aliquota_interna_dest = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_aliq_inte_dest')
    aliquota_interestadual = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='cte_aliq_inter')

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
    tipo_doc = models.CharField(max_length=2, default='00', db_column='ctdo_tipo', verbose_name='Tipo Documento', choices=[('00', 'NFe'), ('01', 'CTe'), ('02', 'DANFE TERCEIROS')]) # 00=NFe

    class Meta:
        managed = True
        db_table = 'cte_documento'


class RegraICMS(models.Model):
    uf_origem = models.CharField(max_length=2)
    uf_destino = models.CharField(max_length=2)

    contribuinte = models.BooleanField()
    simples_nacional = models.BooleanField()

    cfop = models.CharField(max_length=4, null=True, blank=True)
    # opcional: regra específica por CFOP

    aliquota = models.DecimalField(max_digits=5, decimal_places=2)
    aliquota_destino = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Alíquota Interna Destino (DIFAL)")
    reducao_base = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Campos ST
    mva_st = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)
    aliquota_st = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)
    reducao_base_st = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)

    cst = models.CharField(max_length=3)
    csosn = models.CharField(max_length=4, null=True, blank=True)

    diferimento = models.BooleanField(default=False)
    isento = models.BooleanField(default=False)


TIPO_EMITENTE = (
    ('1', 'Transportadora'),
    ('2', 'Trasnporte de carga Própria'),
)

TIPO_CARGA = (
    ('1', 'Granel sólido'),
    ('2', 'Granel liquido'),
    ('3', 'Frigorificada'),
    ('4', 'Conteinerizada'),
    ('5', 'Perigosa'),
    ('6', 'Outra'),
)

TIPO_TRANSPORTADOR = (
    (1, 'ETC - Empresa de Transportes de Carga'),
    (2, 'TAC - Transportadora Autonoma de  Carga'),
    (3, 'CTC - Cooperativa de Transportes de Carga'),
)
# MDFe
class Mdfe(models.Model):
    mdf_id = models.AutoField(primary_key=True, db_column='mdf_id', verbose_name='ID MDFe')
    mdf_empr = models.IntegerField(blank=True, null=True, db_column='mdf_empr', verbose_name='ID Empresa')
    mdf_fili = models.IntegerField(blank=True, null=True, db_column='mdf_fili', verbose_name='ID Filial')
    mdf_nume = models.IntegerField(blank=True, null=True, db_column='mdf_nume', verbose_name='Número do MDFe')
    mdf_seri = models.IntegerField(blank=True, null=True, db_column='mdf_seri', verbose_name='Série')
    mdf_tran = models.IntegerField(blank=True, null=True, db_column='mdf_tran', verbose_name='ID Transportadora')
    mdf_moto = models.IntegerField(blank=True, null=True, db_column='mdf_moto', verbose_name='ID Motorista')
    mdf_veic = models.IntegerField(blank=True, null=True, db_column='mdf_veic', verbose_name='ID Veículo')
    mdf_emis = models.DateField(blank=True, null=True, db_column='mdf_emis', verbose_name='Data de Emissão')
    mdf_xml_mdf = models.TextField(blank=True, null=True, db_column='mdf_xml_mdf', verbose_name='XML MDFe')
    mdf_prot_mdf = models.CharField(max_length=100, blank=True, null=True, db_column='mdf_prot_mdf', verbose_name='Protocolo MDFe')
    mdf_stat = models.IntegerField(blank=True, null=True, db_column='mdf_stat', verbose_name='Status')
    mdf_canc = models.BooleanField(blank=True, null=True, db_column='mdf_canc', verbose_name='Cancelado')
    mdf_fina = models.BooleanField(blank=True, null=True, db_column='mdf_fina', verbose_name='Finalizado')
    mdf_chav = models.CharField(max_length=50, blank=True, null=True, db_column='mdf_chav', verbose_name='Chave MDFe')
    mdf_data_ence = models.DateField(blank=True, null=True, db_column='mdf_data_ence', verbose_name='Data de Encerramento')
    mdf_prot_ence = models.CharField(max_length=100, blank=True, null=True, db_column='mdf_prot_ence', verbose_name='Protocolo de Encerramento')
    mdf_esta_ence = models.CharField(max_length=3, blank=True, null=True, db_column='mdf_esta_ence', verbose_name='Estado de Encerramento')
    mdf_cida_ence = models.CharField(max_length=7, blank=True, null=True, db_column='mdf_cida_ence', verbose_name='Cidade de Encerramento')
    mdf_esta_orig = models.CharField(max_length=2, blank=True, null=True, db_column='mdf_esta_orig', verbose_name='Estado Origem')
    mdf_esta_dest = models.CharField(max_length=2, blank=True, null=True, db_column='mdf_esta_dest', verbose_name='Estado Destino')
    mdf_cida_carr = models.CharField(max_length=7, blank=True, null=True, db_column='mdf_cida_carr', verbose_name='Cidade do carregamento')
    mdf_nume_lote = models.IntegerField(blank=True, null=True, db_column='mdf_nume_lote', verbose_name='Número do Lote')
    mdf_esta_pass = models.CharField(max_length=60, blank=True, null=True, db_column='mdf_esta_pass', verbose_name='Estados do Passagem')
    mdf_tipo_emit = models.CharField(max_length=1, blank=True, null=True, db_column='mdf_tipo_emit', verbose_name='Tipo de Emitente', choices=TIPO_EMITENTE)
    mdf_pred_carg = models.CharField(max_length=2, blank=True, null=True, db_column='mdf_pred_carg', verbose_name='Tipo da Carga', choices=TIPO_CARGA)
    mdf_pred_xprod = models.CharField(max_length=120, blank=True, null=True, db_column='mdf_pred_xprod', verbose_name='Descrição do Produto')
    mdf_pred_ncm = models.CharField(max_length=8, blank=True, null=True, db_column='mdf_pred_ncm', verbose_name='NCM')
    mdf_pred_ean = models.CharField(max_length=14, blank=True, null=True, db_column='mdf_pred_ean', verbose_name='EAN')
    mdf_cep_loca_carg = models.CharField(max_length=8, blank=True, null=True, db_column='mdf_cep_loca_carg', verbose_name='CEP do Local de Carga')
    mdf_cep_loca_desc = models.CharField(max_length=8, blank=True, null=True, db_column='mdf_cep_loca_desc', verbose_name='Descrição do Local de Carga')
    mdf_tipo_tran = models.IntegerField(blank=True, null=True, db_column='mdf_tipo_tran', verbose_name='Tipo de Transportador', choices=TIPO_TRANSPORTADOR)
    mdf_nome_carr = models.CharField(max_length=60, blank=True, null=True, db_column='mdf_nome_carr', verbose_name='Nome do local de  Carregamento')
    class Meta:
        managed = False
        db_table = 'mdfe'
        verbose_name = 'MDFe'
        verbose_name_plural = 'MDFes'


class MdfeDocumento(models.Model):
    id = models.AutoField(primary_key=True)
    mdfe = models.ForeignKey(Mdfe, on_delete=models.CASCADE, db_column="mdfd_mdfe_id", related_name="documentos", db_constraint=False)
    tipo_doc = models.CharField(
        max_length=2,
        default="00",
        db_column="mdfd_tipo",
        verbose_name="Tipo Documento",
        choices=[("00", "NFe"), ("01", "CTe")],
    )
    chave = models.CharField(max_length=44, blank=True, null=True, db_column="mdfd_chave", verbose_name="Chave (44 dígitos)")
    cmun_descarga = models.CharField(max_length=7, blank=True, null=True, db_column="mdfd_cmun_desc", verbose_name="Município Descarga (IBGE)")
    xmun_descarga = models.CharField(max_length=60, blank=True, null=True, db_column="mdfd_xmun_desc", verbose_name="Nome Município Descarga")

    class Meta:
        managed = True
        db_table = "mdfe_documento"



class Mdfeantt(models.Model):
    mdfe_antt_id = models.IntegerField(primary_key=True, db_column='mdfe_antt_id', verbose_name='ID MDFe ANTT')
    mdfe_antt_rntrc = models.IntegerField(blank=True, null=True, db_column='mdfe_antt_rntrc', verbose_name='RNTRC')
    mdfe_antt_ciot = models.IntegerField(blank=True, null=True, db_column='mdfe_antt_ciot', verbose_name='CIOT')
    mdfe_antt_cpf = models.CharField(max_length=11, blank=True, null=True, db_column='mdfe_antt_cpf', verbose_name='CPF')
    mdfe_antt_cnpj = models.CharField(max_length=14, blank=True, null=True, db_column='mdfe_antt_cnpj', verbose_name='CNPJ')
    mdfe_antt_mdfe = models.ForeignKey('Mdfe', models.DO_NOTHING, db_column='mdfe_antt_mdfe_id', verbose_name='ID MDFe')

    class Meta:
        managed = False
        db_table = 'mdfeantt'



class Mdfecontratante(models.Model):
    mdfe_cont_id = models.IntegerField(primary_key=True, db_column='mdfe_cont_id', verbose_name='ID Contratante')
    mdfe_cont_mdfe = models.ForeignKey('Mdfe', models.DO_NOTHING, db_column='mdfe_cont_mdfe_id', verbose_name='ID MDFe')
    mdfe_cont_cont = models.IntegerField(blank=True, null=True, db_column='mdfe_cont_cont', verbose_name='ID Contratante')
    mdfe_cont_cnpj_cpf = models.CharField(max_length=255, blank=True, null=True, db_column='mdfe_cont_cnpj_cpf', verbose_name='CNPJ ou CPF do Contratante')

    class Meta:
        managed = False
        db_table = 'mdfecontratante'
        verbose_name = 'MDFe Contratante'
        verbose_name_plural = 'MDFes Contratantes'
        

RESPONSAVEL_SEGURO = (
    (1, 'Emitente'),
    (2, 'Contratante'),
)

class Mdfeseguro(models.Model):
    mdfe_segu_id = models.IntegerField(primary_key=True, db_column='mdfe_segu_id', verbose_name='ID Seguro')
    mdfe_segu_mdfe = models.ForeignKey('Mdfe', models.DO_NOTHING, db_column='mdfe_segu_mdfe_id', verbose_name='ID MDFe')
    mdfe_segu_resp = models.IntegerField(blank=True, null=True, db_column='mdfe_segu_resp', verbose_name='ID Responsável', choices=RESPONSAVEL_SEGURO)
    mdfe_segu_cnpj_resp = models.CharField(max_length=14, blank=True, null=True, db_column='mdfe_segu_cnpj_resp', verbose_name='CNPJ do Responsável')
    mdfe_segu_cpf_resp = models.CharField(max_length=11, blank=True, null=True, db_column='mdfe_segu_cpf_resp', verbose_name='CPF do Responsável')
    mdfe_segu_nome_segu = models.CharField(max_length=30, blank=True, null=True, db_column='mdfe_segu_nome_segu', verbose_name='Nome do Seguro')
    mdfe_segu_cnpj_segu = models.CharField(max_length=14, blank=True, null=True, db_column='mdfe_segu_cnpj_segu', verbose_name='CNPJ do Seguro')
    mdfe_segu_apol = models.CharField(max_length=20, blank=True, null=True, db_column='mdfe_segu_apol', verbose_name='Número do Apólice')
    mdfe_segu_aver = models.CharField(max_length=40, blank=True, null=True, db_column='mdfe_segu_aver', verbose_name='Número da averbação')

    class Meta:
        managed = False
        db_table = 'mdfeseguro'




class Bombas(models.Model):
    bomb_empr = models.IntegerField(primary_key=True, db_column='bomb_empr', verbose_name='Empresa Bomba')
    bomb_codi = models.CharField(max_length=10, blank=True, null=True, db_column='bomb_codi', verbose_name='Código Bomba')
    bomb_desc = models.CharField(max_length=60, blank=True, null=True, db_column='bomb_desc', verbose_name='Descrição Bomba')
    bomb_cecu = models.IntegerField(blank=True, null=True, db_column='bomb_cecu', verbose_name='Centro de custo da Bomba')
    bomb_forn = models.BigIntegerField(blank=True, null=True, db_column='bomb_forn', verbose_name='Fornecedor da Bomba')
    bomb_obse = models.TextField(blank=True, null=True, db_column='bomb_obse', verbose_name='Observação Bomba')
    
    class Meta:
        managed = False
        db_table = 'bomba'
        verbose_name = 'Bomba'
        verbose_name_plural = 'Bombas'
        ordering = ['bomb_empr', 'bomb_codi']
        unique_together = (('bomb_empr', 'bomb_codi'),)
    
    def __str__(self):
        return f"{self.bomb_empr} - {self.bomb_codi} - {self.bomb_desc}"





class BombasSaldos(models.Model):
    TIPO_MOVIMENTACAO = (
    (1, 'Entrada'),
    (2, 'Saída'),
)
    bomb_id = models.BigAutoField(primary_key=True, db_column='bomb_id')
    bomb_empr = models.IntegerField(db_column='bomb_empr', verbose_name='Empresa Bomba')
    bomb_fili = models.IntegerField(verbose_name='Filial Bomba')
    bomb_bomb = models.CharField(max_length=10, blank=True, null=True, db_column='bomb_bomb', verbose_name='Código Bomba')
    bomb_comb = models.CharField(max_length=10, blank=True, null=True, db_column='bomb_comb', verbose_name='Combustível')
    bomb_sald = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, db_column='bomb_sald', verbose_name='Quantidade Movimentada')
    bomb_tipo_movi = models.IntegerField(blank=True, null=True, db_column='bomb_tipo_movi', verbose_name='Tipo Movimentação', choices=TIPO_MOVIMENTACAO)
    bomb_data = models.DateField(blank=True, null=True, db_column='bomb_data', verbose_name='Data Movimentação')
    bomb_usua = models.IntegerField(blank=True, null=True, db_column='bomb_usua', verbose_name='Usuário Movimentação')
    
    class Meta:
        managed = False
        db_table = 'bombasaldos'
        verbose_name = 'Bomba Saldo'
        verbose_name_plural = 'Bombas Saldos'
        ordering = ['bomb_empr', 'bomb_fili', 'bomb_bomb', 'bomb_comb', '-bomb_data', '-bomb_id']
    
    def __str__(self):
        return f"{self.bomb_empr} - {self.bomb_bomb} - {self.bomb_comb} - {self.bomb_sald}"


class Abastecusto(models.Model):
    abas_empr = models.IntegerField(primary_key=True, verbose_name='Empresa Abastecimento')
    abas_fili = models.IntegerField(verbose_name='Filial Abastecimento')
    abas_ctrl = models.IntegerField(verbose_name='Controle Abastecimento')
    abas_frot = models.CharField(max_length=10, blank=True, null=True, verbose_name='Frota/Transportadora')
    abas_veic_sequ = models.IntegerField(blank=True, null=True, verbose_name='Veículo Sequencial')
    abas_plac = models.CharField(max_length=7, blank=True, null=True, verbose_name='Placa')
    abas_data = models.DateField(blank=True, null=True, verbose_name='Data Abastecimento')
    abas_func = models.IntegerField(blank=True, null=True, verbose_name='Funcionário Abastecimento')
    abas_enti = models.IntegerField(blank=True, null=True, verbose_name='Entidade Abastecimento')
    abas_bomb = models.CharField(max_length=10, blank=True, null=True, verbose_name='Bomba Abastecimento')
    abas_comb = models.CharField(max_length=20, blank=True, null=True, verbose_name='Combustível Abastecimento')
    abas_quan = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name='Quantidade Abastecimento')
    abas_unit = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name='Preço Unitário Abastecimento')
    abas_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Total Abastecimento')
    abas_hokm = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Horimetro Abastecimento')
    abas_hokm_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Horimetro Anterior Abastecimento')
    abas_obse = models.TextField(blank=True, null=True, verbose_name='Observação Abastecimento')
    abas_quan_ante = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name='Quantidade Anterior Abastecimento')
    abas_medi = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Medidor Abastecimento')
    abas_docu = models.DecimalField(max_digits=15, decimal_places=0, blank=True, null=True, verbose_name='Documento Abastecimento')
    abas_usua_nome = models.IntegerField(blank=True, null=True, verbose_name='Usuário Abastecimento')
    abas_usua_alte = models.IntegerField(blank=True, null=True, verbose_name='Usuário Alteração')


    class Meta:
        managed = False
        db_table = 'abastecusto'
        unique_together = (('abas_empr', 'abas_fili', 'abas_ctrl'),)
        
        
        

class Custos(models.Model):
    lacu_empr = models.IntegerField(verbose_name='Empresa')
    lacu_fili = models.IntegerField(verbose_name='Filial')
    lacu_ctrl = models.DecimalField(max_digits=9, decimal_places=0, verbose_name='Controle')
    lacu_data = models.DateField(blank=True, null=True, verbose_name='Data Custos')
    lacu_item = models.CharField(max_length=20, blank=True, null=True, verbose_name='Item/Insumo')
    lacu_nome_item = models.CharField(max_length=60, blank=True, null=True, verbose_name='Descrição Item')
    lacu_quan = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True, verbose_name='Quantidade')
    lacu_unit = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name='Preço Unitário')
    lacu_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Total')
    lacu_daga = models.DateField(blank=True, null=True, verbose_name='Data Garantia')
    lacu_kmga = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Km Garantia')
    lacu_cecu = models.IntegerField(blank=True, null=True, verbose_name='Custos de Execução')
    lacu_kmat = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Km Matriz')
    lacu_veic = models.IntegerField(verbose_name='Veículo')
    lacu_frot = models.CharField(max_length=20, verbose_name='Frota/Transportadora')
    lacu_tran = models.IntegerField(verbose_name='Nome da Transportadora')
    lacu_moto = models.IntegerField(verbose_name='Motorista')
    lacu_docu = models.CharField(max_length=25, verbose_name='Documento')
    lacu_forn = models.IntegerField(verbose_name='Fornecedor')
    lacu_nome_forn = models.CharField(max_length=60, blank=True, null=True, verbose_name='Nome Fornecedor')
    lacu_veic = models.IntegerField(blank=True, null=True, verbose_name='Veículo')
    lacu_moto = models.IntegerField(blank=True, null=True, verbose_name='Motorista')
    lacu_docu = models.CharField(max_length=25, blank=True, null=True, verbose_name='Documento')
    lacu_obse = models.TextField(blank=True, null=True, verbose_name='Observação')
    lacu_nota = models.DecimalField(max_digits=9, decimal_places=0, blank=True, null=True, verbose_name='Nota Fiscal')
    lacu_cupo = models.DecimalField(max_digits=9, decimal_places=0, blank=True, null=True, verbose_name='Cupom')
    lacu_comp = models.BooleanField(blank=True, null=True, verbose_name='Completado')
 
    lacu_id = models.AutoField(primary_key=True, verbose_name='ID')
    class Meta:
        managed = False
        db_table = 'custos'
        ordering = ['lacu_id']
