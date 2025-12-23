from django.db import models

FINANCEIRO_OS = [
    (99, 'SEM FINANCEIRO'),
    (00, 'DUPLICATA'),
    (1, 'CHEQUE'),
    (2, 'PROMISSÓRIA'),
    (3, 'RECIBO'),
    (50, 'CHEQUE-PRÉ'),
    (51, 'CARTÃO DE CRÉDITO'),
    (52, 'CARTÃO DE DÉBITO'),
    (53, 'BOLETO'),
    (54, 'DINHEIRO'),
    (55, 'DEPÓSITO EM CONTA'),
    (60, 'PIX')
]


ORDEM_STATUS_CHOICES = (
    (0, "Aberta"),
    (1, "Orçamento gerado"),
    (2, "Aguardando Liberação"),
    (3, "Cancelada"),
    (4, "Finalizada"),
    (5, "Reprovada"),
    (20, "Faturada_parcial"),
    (21, "Em atraso"),
)

class Os(models.Model):
    os_empr = models.IntegerField()
    os_fili = models.IntegerField()
    os_os = models.IntegerField(primary_key=True)
    os_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    os_orig = models.CharField(max_length=100, blank=True, null=True)
    os_data_aber = models.DateField()
    os_hora_aber = models.TimeField(blank=True, null=True)
    os_clie = models.IntegerField(blank=True, null=True)
    os_prof_aber = models.IntegerField(blank=True, null=True)
    os_fina_os = models.IntegerField(blank=True, null=True, choices=FINANCEIRO_OS, default=99)
    os_obje_os = models.TextField(blank=True, null=True)
    os_fabr = models.IntegerField(blank=True, null=True)
    os_marc = models.IntegerField(blank=True, null=True)
    os_mode = models.IntegerField(blank=True, null=True)
    os_hori = models.DecimalField(max_digits=15, decimal_places=1, blank=True, null=True)
    os_plac = models.CharField(max_length=40, blank=True, null=True)
    os_pref = models.CharField(max_length=30, blank=True, null=True)
    os_cont = models.CharField(max_length=40, blank=True, null=True)
    os_prob_rela = models.TextField(blank=True, null=True)
    os_stat_os = models.IntegerField(blank=True, null=True, choices=ORDEM_STATUS_CHOICES, default=0)
    os_situ = models.IntegerField(blank=True, null=True)
    os_nota_peca = models.CharField(max_length=20, blank=True, null=True)
    os_nota_serv = models.CharField(max_length=100, blank=True, null=True)
    os_tem_peca = models.BooleanField(blank=True, null=True)
    os_tem_serv = models.BooleanField(blank=True, null=True)
    os_moti_canc = models.TextField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True) 
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True) 
    os_loca_apli = models.TextField(blank=True, null=True, verbose_name="Localização da Aplicação/Trabalho")
    os_ende_apli = models.TextField(blank=True, null=True)
    os_resp = models.IntegerField(blank=True, null=True)
    os_obse = models.TextField(blank=True, null=True)
    os_plac_1 = models.CharField(max_length=40, blank=True, null=True)
    os_data_entr = models.DateField(blank=True, null=True)
    os_data_fech = models.DateField(blank=True, null=True)
    os_desc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    os_auto = models.CharField(max_length=60, blank=True, null=True)
    os_praz_paga = models.CharField(max_length=100, blank=True, null=True)
    os_com_fina = models.BooleanField(blank=True, null=True)
    os_ja_proc = models.BooleanField(blank=True, null=True)
    os_rena = models.CharField(max_length=11, blank=True, null=True)
    os_chas = models.CharField(max_length=17, blank=True, null=True)
    os_moto = models.CharField(max_length=255, blank=True, null=True)
    os_fech_obse = models.TextField(blank=True, null=True)
    os_seto = models.IntegerField(blank=True, null=True)    
    os_assi_clie = models.BinaryField(null=True, blank=True)   # assinatura do cliente
    os_assi_oper = models.BinaryField(null=True, blank=True)   # assinatura do operador

    class Meta:
        managed = False
        db_table = 'os'
        unique_together = (('os_empr', 'os_fili', 'os_os'),)
    
    def calcular_total(self):
            total_pecas = sum(
                peca.peca_tota or 0 
                for peca in PecasOs.objects.filter(
                    peca_empr=self.os_empr,
                    peca_fili=self.os_fili,
                    peca_os=self.os_os
                )
            )
            
            total_servicos = sum(
                servico.serv_tota or 0
                for servico in ServicosOs.objects.filter(
                    serv_empr=self.os_empr,
                    serv_fili=self.os_fili,
                    serv_os=self.os_os
                )
            )
            
            self.os_tota = total_pecas + total_servicos
            return self.os_tota


class PecasOs(models.Model):
    peca_empr = models.IntegerField()
    peca_fili = models.IntegerField()
    peca_os = models.IntegerField()
    peca_item = models.IntegerField(db_column='peca_item',primary_key=True)
    peca_prod = models.CharField(max_length=20, blank=True, null=True)
    peca_quan = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    peca_unit = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    peca_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    peca_data = models.DateField(blank=True, null=True)
    peca_prof = models.IntegerField(blank=True, null=True)
    peca_obse = models.TextField(blank=True, null=True)
    peca_moes = models.BooleanField(blank=True, null=True)
    peca_desc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.
    selecionado = models.BooleanField(blank=True, null=True)
    peca_perc_desc = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    peca_impr = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'pecasos'
        unique_together = (('peca_empr', 'peca_fili', 'peca_os', 'peca_item'),)

    def update_estoque(self, quantidade):
        try:
            from Produtos.models import SaldoProduto
            # Busca o saldo do produto na empresa/filial da OS
            # Usando filter().first() para evitar erros se não existir
            saldo = SaldoProduto.objects.using(self._state.db).filter(
                produto_codigo=self.peca_prod,
                empresa=self.peca_empr,
                filial=self.peca_fili
            ).first()
            
            if saldo:
                saldo.saldo_estoque += quantidade
                saldo.save(using=self._state.db)
        except Exception:
            pass
    



class ServicosOs(models.Model):
    serv_empr = models.IntegerField()
    serv_fili = models.IntegerField()
    serv_os = models.IntegerField()
    serv_item = models.IntegerField(primary_key=True)
    serv_prod = models.CharField(max_length=20, blank=True, null=True)
    serv_quan = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    serv_unit = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    serv_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    serv_data = models.DateField(blank=True, null=True)
    serv_prof = models.IntegerField(blank=True, null=True)
    serv_obse = models.TextField(blank=True, null=True)
    serv_desc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.
    serv_perc_desc = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    serv_impr = models.BooleanField(blank=True, null=True)
    serv_stat = models.IntegerField(blank=True, null=True, default=0)
    serv_data_hora_impr = models.DateTimeField(blank=True, null=True)
    serv_stat_seto = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'servicosos'
        unique_together = (('serv_empr', 'serv_fili', 'serv_os', 'serv_item'),)

    def update_estoque(self, quantidade):
        try:
            from Produtos.models import SaldoProduto
            saldo = SaldoProduto.objects.using(self._state.db).filter(
                produto_codigo=self.serv_prod,
                empresa=self.serv_empr,
                filial=self.serv_fili
            ).first()
            
            if saldo:
                saldo.saldo_estoque += quantidade
                saldo.save(using=self._state.db)
        except Exception:
            pass
        

class OsHora(models.Model):
    os_hora_empr = models.IntegerField()
    os_hora_fili = models.IntegerField()
    os_hora_os = models.IntegerField() 
    os_hora_item = models.IntegerField(primary_key=True)

    os_hora_data = models.DateField()

    # Manhã
    os_hora_manh_ini = models.TimeField(null=True, blank=True)
    os_hora_manh_fim = models.TimeField(null=True, blank=True)

    # Tarde
    os_hora_tard_ini = models.TimeField(null=True, blank=True)
    os_hora_tard_fim = models.TimeField(null=True, blank=True)

    os_hora_tota = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # KM
    os_hora_km_sai = models.IntegerField(null=True, blank=True)
    os_hora_km_che = models.IntegerField(null=True, blank=True)

    os_hora_oper = models.IntegerField(null=True, blank=True)       # operador
    os_hora_equi = models.CharField(max_length=100, null=True, blank=True)
    os_hora_obse = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'os_hora'
        unique_together = (('os_hora_empr', 'os_hora_fili', 'os_hora_os', 'os_hora_item'),)



#Os_geral view para o dashboard de os
class OrdemServicoGeral(models.Model):
    empresa = models.IntegerField()
    filial = models.IntegerField()
    ordem_de_servico = models.IntegerField(primary_key=True)
    cliente = models.IntegerField()
    nome_cliente = models.CharField(max_length=100)
    data_abertura = models.DateField()
    data_fim = models.DateField(null=True)
    situacao_os = models.CharField(max_length=50)
    vendedor = models.IntegerField()
    nome_vendedor = models.CharField(max_length=100)
    pecas = models.TextField()
    servicos = models.TextField()
    total_os = models.DecimalField(max_digits=12, decimal_places=2)
    status_os = models.CharField(max_length=50)  # já vem como label
    responsavel = models.IntegerField()
    atendente = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'os_geral'
