from django.db import models
from django.contrib.postgres.fields import JSONField


class NfseConfiguracaoMunicipio(models.Model):
    nfmc_id = models.AutoField(primary_key=True)
    nfmc_empr = models.IntegerField(verbose_name='Empresa')
    nfmc_fili = models.IntegerField(verbose_name='Filial')
    nfmc_codi_muni = models.CharField(max_length=10, verbose_name='Código Município')
    nfmc_nome_muni = models.CharField(max_length=120, verbose_name='Nome Município')

    nfmc_prov = models.CharField(max_length=30, default='nacional', verbose_name='Provedor')
    nfmc_usa_naci = models.BooleanField(default=True, verbose_name='Usa NFS-e Nacional')
    nfmc_ambi = models.CharField(max_length=20, default='homologacao', verbose_name='Ambiente')

    nfmc_url_emis = models.CharField(max_length=255, blank=True, null=True, verbose_name='URL Emissão')
    nfmc_url_cons = models.CharField(max_length=255, blank=True, null=True, verbose_name='URL Consulta')
    nfmc_url_canc = models.CharField(max_length=255, blank=True, null=True, verbose_name='URL Cancelamento')
    nfmc_wsdl = models.CharField(max_length=255, blank=True, null=True, verbose_name='WSDL')

    nfmc_soap_act_emis = models.CharField(max_length=100, blank=True, null=True, verbose_name='SOAP Action Emissão')
    nfmc_soap_act_cons = models.CharField(max_length=100, blank=True, null=True, verbose_name='SOAP Action Consulta')
    nfmc_soap_act_canc = models.CharField(max_length=100, blank=True, null=True, verbose_name='SOAP Action Cancelamento')

    nfmc_seri_rps = models.CharField(max_length=20, blank=True, null=True, verbose_name='Série RPS')
    nfmc_exig_lote = models.BooleanField(default=False, verbose_name='Exige Lote')
    nfmc_exig_assi = models.BooleanField(default=False, verbose_name='Exige Assinatura')

    nfmc_usua = models.CharField(max_length=120, blank=True, null=True, verbose_name='Usuário')
    nfmc_senh = models.CharField(max_length=120, blank=True, null=True, verbose_name='Senha')
    nfmc_token = models.TextField(blank=True, null=True, verbose_name='Token')
    nfmc_cert = models.CharField(max_length=120, blank=True, null=True, verbose_name='Alias Certificado')

    nfmc_obse = models.TextField(blank=True, null=True, verbose_name='Observações')

    class Meta:
        db_table = 'nfse_configuracao_municipio'
        ordering = ['nfmc_id']
        verbose_name = 'Configuração Município NFS-e'
        verbose_name_plural = 'Configurações Municípios NFS-e'
        indexes = [
            models.Index(fields=['nfmc_empr', 'nfmc_fili', 'nfmc_codi_muni']),
            models.Index(fields=['nfmc_prov']),
        ]

    def __str__(self):
        return f'{self.nfmc_nome_muni} - {self.nfmc_codi_muni}'

class Nfse(models.Model):
    nfse_id = models.AutoField(primary_key=True)
    nfse_empr = models.IntegerField(verbose_name='Empresa')
    nfse_fili = models.IntegerField(verbose_name='Filial')

    nfse_nume = models.CharField(max_length=30, blank=True, null=True, verbose_name='Número NFS-e')
    nfse_rps_nume = models.CharField(max_length=30, verbose_name='Número RPS')
    nfse_rps_seri = models.CharField(max_length=20, blank=True, null=True, verbose_name='Série RPS')

    nfse_codi_veri = models.CharField(max_length=100, blank=True, null=True, verbose_name='Código Verificação')
    nfse_prot = models.CharField(max_length=100, blank=True, null=True, verbose_name='Protocolo')
    nfse_statu = models.CharField(max_length=30, default='rascunho', verbose_name='Status')

    nfse_muni_codi = models.CharField(max_length=10, verbose_name='Código Município')
    nfse_muni_nome = models.CharField(max_length=120, blank=True, null=True, verbose_name='Nome Município')

    nfse_pres_doc = models.CharField(max_length=20, verbose_name='Documento Prestador')
    nfse_pres_nome = models.CharField(max_length=120, verbose_name='Nome Prestador')
    nfse_pres_muni_inci = models.CharField(max_length=10, blank=True, null=True, verbose_name='Município Incidência')

    nfse_tom_doc = models.CharField(max_length=20, blank=True, null=True, verbose_name='Documento Tomador')
    nfse_tom_nome = models.CharField(max_length=120, blank=True, null=True, verbose_name='Nome Tomador')
    nfse_tom_ie = models.CharField(max_length=30, blank=True, null=True, verbose_name='IE Tomador')
    nfse_tom_im = models.CharField(max_length=30, blank=True, null=True, verbose_name='IM Tomador')
    nfse_tom_email = models.CharField(max_length=120, blank=True, null=True, verbose_name='Email Tomador')
    nfse_tom_fone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Fone Tomador')
    nfse_tom_ende = models.CharField(max_length=255, blank=True, null=True, verbose_name='Endereço Tomador')
    nfse_tom_nume = models.CharField(max_length=20, blank=True, null=True, verbose_name='Número Tomador')
    nfse_tom_bair = models.CharField(max_length=80, blank=True, null=True, verbose_name='Bairro Tomador')
    nfse_tom_cepe = models.CharField(max_length=10, blank=True, null=True, verbose_name='CEP Tomador')
    nfse_tom_cida = models.CharField(max_length=120, blank=True, null=True, verbose_name='Cidade Tomador')
    nfse_tom_esta = models.CharField(max_length=2, blank=True, null=True, verbose_name='UF Tomador')

    nfse_serv_codi = models.CharField(max_length=30, verbose_name='Código Serviço')
    nfse_serv_desc = models.TextField(verbose_name='Descrição Serviço')
    nfse_serv_cnae = models.CharField(max_length=20, blank=True, null=True, verbose_name='CNAE')
    nfse_serv_lc116 = models.CharField(max_length=20, blank=True, null=True, verbose_name='Código LC116')
    nfse_serv_muni = models.CharField(max_length=10, blank=True, null=True, verbose_name='Município Serviço')
    nfse_natu_oper = models.CharField(max_length=30, blank=True, null=True, verbose_name='Natureza Operação')

    nfse_val_serv = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor Serviço')
    nfse_val_dedu = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor Dedução')
    nfse_val_desc = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor Desconto')
    nfse_val_inss = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor INSS')
    nfse_val_irrf = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor IRRF')
    nfse_val_csll = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor CSLL')
    nfse_val_cofi = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor COFINS')
    nfse_val_pis = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor PIS')
    nfse_val_iss = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor ISS')
    nfse_val_liqu = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor Líquido')
    nfse_aliq_iss = models.DecimalField(max_digits=7, decimal_places=4, default=0, verbose_name='Alíquota ISS')

    nfse_iss_ret = models.BooleanField(default=False, verbose_name='ISS Retido')

    nfse_payl_envi = JSONField(blank=True, null=True, verbose_name='Payload Envio')
    nfse_res_envi = JSONField(blank=True, null=True, verbose_name='Resposta Envio')
    nfse_xml_envi = models.TextField(blank=True, null=True, verbose_name='XML Envio')
    nfse_xml_ret = models.TextField(blank=True, null=True, verbose_name='XML Retorno')
    nfse_mess_err = models.TextField(blank=True, null=True, verbose_name='Mensagem Erro')

    nfse_data_comp = models.DateField(blank=True, null=True, verbose_name='Data Competência')
    nfse_data_emis = models.DateTimeField(blank=True, null=True, verbose_name='Data Emissão')
    nfse_data_canc = models.DateTimeField(blank=True, null=True, verbose_name='Data Cancelamento')

    class Meta:
        db_table = 'nfse'
        ordering = ['-nfse_id']
        verbose_name = 'NFS-e'
        verbose_name_plural = 'NFS-e'
        indexes = [
            models.Index(fields=['nfse_empr', 'nfse_fili', 'nfse_statu']),
            models.Index(fields=['nfse_empr', 'nfse_fili', 'nfse_rps_nume']),
            models.Index(fields=['nfse_muni_codi']),
            models.Index(fields=['nfse_nume']),
        ]

    def __str__(self):
        return f'NFS-e {self.nfse_nume or self.nfse_rps_nume}'

class NfseItem(models.Model):
    nfsi_id = models.AutoField(primary_key=True)
    nfsi_empr = models.IntegerField(verbose_name='Empresa')
    nfsi_fili = models.IntegerField(verbose_name='Filial')
    nfsi_nfse_id = models.IntegerField(verbose_name='ID NFS-e')

    nfsi_orde = models.IntegerField(default=1, verbose_name='Ordem')
    nfsi_desc = models.TextField(verbose_name='Descrição')
    nfsi_qtde = models.DecimalField(max_digits=15, decimal_places=4, default=1, verbose_name='Quantidade')
    nfsi_unit = models.DecimalField(max_digits=15, decimal_places=6, default=0, verbose_name='Valor Unitário')
    nfsi_tota = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor Total')

    nfsi_serv_codi = models.CharField(max_length=30, blank=True, null=True, verbose_name='Código Serviço')
    nfsi_cnae = models.CharField(max_length=20, blank=True, null=True, verbose_name='CNAE')
    nfsi_lc116 = models.CharField(max_length=20, blank=True, null=True, verbose_name='LC116')

    class Meta:
        db_table = 'nfse_item'
        ordering = ['nfsi_id']
        verbose_name = 'Item NFS-e'
        verbose_name_plural = 'Itens NFS-e'
        indexes = [
            models.Index(fields=['nfsi_nfse_id']),
            models.Index(fields=['nfsi_empr', 'nfsi_fili']),
        ]

    def __str__(self):
        return self.nfsi_desc[:60]


class NfseEvento(models.Model):
    nfsev_id = models.AutoField(primary_key=True)
    nfsev_empr = models.IntegerField(verbose_name='Empresa')
    nfsev_fili = models.IntegerField(verbose_name='Filial')
    nfsev_nfse_id = models.IntegerField(verbose_name='ID NFS-e')
    nfsev_tip = models.CharField(max_length=30, verbose_name='Tipo')
    nfsev_payl = JSONField(blank=True, null=True, verbose_name='Payload')
    nfsev_ret = JSONField(blank=True, null=True, verbose_name='Retorno')
    nfsev_desc = models.TextField(blank=True, null=True, verbose_name='Descrição')
    nfsev_data = models.DateTimeField(auto_now_add=True, verbose_name='Data')

    class Meta:
        db_table = 'nfse_evento'
        ordering = ['-nfsev_id']
        verbose_name = 'Evento NFS-e'
        verbose_name_plural = 'Eventos NFS-e'
        indexes = [
            models.Index(fields=['nfsev_nfse_id']),
            models.Index(fields=['nfsev_tip']),
        ]

    def __str__(self):
        return f'{self.nfsev_tip} - {self.nfsev_nfse_id}'