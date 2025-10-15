from django.db import models
from django.db import transaction
from django.db.models import Max
from django.utils import timezone


ORDEM_STATUS_CHOICES = (
    (0, "Aberta"),
    (1, "Orçamento gerado"),
    (2, "Aguardando Liberação"),
    (3, "Liberada"),
    (4, "Finalizada"),
    (5, "Reprovada"),
    (20, "Faturada_parcial"),
    (21, "Em atraso"),
)


Ordem_Prioridade_Choices = (
    ("0", "Normal"),
    ( "1", "Alerta"),
    ( "2", "Urgente")
)


OrdensTipos =(
   ("1", "Motor C.A "),
   ("2", "Motor C.C"),
   ("3", "Motor E.X"),
   ("4", "Motor Sincrono"),
   ("5", "Motor Monofásico"),
   ("6", "Transformador"),
   ("7", "Servo Motor"),
   ("8", "Drives"),
   ("9", "Campo M.C.A"),
   ("10", "Campo Transformador"),
   ("11", "Campo Geral"),
   ("12", "Motor Bomba"),
   ("13", "Bomba"),
   ("14", "Redutor"),
   ("15", "Gerador"),
   ("16", "Eixo"),
   ("17", "Carcaça"),
   
)

class OrdemServicoFaseSetor(models.Model):
    osfs_codi = models.IntegerField(primary_key=True)
    osfs_nome = models.CharField(max_length=100)

    class Meta:
        db_table = 'ordemservicofasesetor'
        managed = False

    def __str__(self):
        return self.osfs_nome


class WorkflowSetor(models.Model):
    """Modelo para definir a sequência de setores no workflow das O.S."""
    wkfl_id = models.AutoField(primary_key=True)
    wkfl_seto_orig = models.IntegerField()
    wkfl_seto_dest = models.IntegerField()
    wkfl_orde = models.IntegerField(default=1)  # Ordem na sequência
    wkfl_ativo = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'workflow_setor'
        unique_together = (('wkfl_seto_orig', 'wkfl_seto_dest'),)
        ordering = ['wkfl_orde']

    def __str__(self):
        return f"Setor {self.wkfl_seto_orig} -> Setor {self.wkfl_seto_dest}"


class HistoricoWorkflow(models.Model):
    """Histórico de movimentações entre setores"""
    hist_id = models.AutoField(primary_key=True)
    hist_empr = models.IntegerField()
    hist_fili = models.IntegerField()
    hist_orde = models.IntegerField()
    hist_seto_orig = models.IntegerField(null=True, blank=True)
    hist_seto_dest = models.IntegerField()
    hist_usua = models.IntegerField()
    hist_data = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'historico_workflow'
        ordering = ['-hist_data']

    def __str__(self):
        return f"O.S. {self.hist_orde} - Setor {self.hist_seto_orig} -> {self.hist_seto_dest}"


class Ordemservico(models.Model):
    orde_empr = models.IntegerField() 
    orde_fili = models.IntegerField()
    orde_nume = models.IntegerField(primary_key=True)  
    
    #Abertura da OS no mobile por tipo
    orde_tipo = models.CharField(max_length=20, choices=OrdensTipos, default="1")
    orde_pote = models.CharField(max_length=100, blank=True, null=True, verbose_name="Potencia")  
    orde_volt = models.IntegerField(blank=True, null=True, verbose_name="Voltagem")
    orde_ampe = models.CharField(max_length=50, blank=True, null=True, verbose_name="Amperagem")
    orde_rpm = models.CharField(max_length=40, blank=True, null=True, verbose_name="Rotação por Minuto")
    orde_marc = models.IntegerField(blank=True, null=True, verbose_name="Marca")
    orde_hz = models.CharField(max_length=50, blank=True, null=True, verbose_name="Frequência")
    orde_seri = models.CharField(max_length=200, blank=True, null=True, verbose_name="NºSerie")
    orde_mode = models.CharField(max_length=200, blank=True, null=True, verbose_name="Modelo")
    orde_patr = models.CharField(max_length=100, blank=True, null=True, verbose_name="TAG")
    orde_cond = models.IntegerField(blank=True, null=True, verbose_name="Condição de recebimento")
    orde_polo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Polos")
    orde_foco = models.CharField(max_length=100, blank=True, null=True, verbose_name="Forma Construtiva")
    orde_esta_chap = models.CharField(max_length=50, blank=True, null=True, verbose_name="Chapas")
    orde_esta_comp = models.CharField(max_length=50, blank=True, null=True, verbose_name="Componentes")
    orde_esta_cabo = models.CharField(max_length=50, blank=True, null=True, verbose_name="Cabos")
    orde_esta_quan_cabo = models.CharField(max_length=50, blank=True, null=True, verbose_name="Quantidade de Cabos")
    orde_esta_fio = models.CharField(max_length=50, blank=True, null=True, verbose_name="Fios")
    orde_esta_quan_fio = models.CharField(max_length=50, blank=True, null=True, verbose_name="Quantidade de Fios")
    orde_esta_larg = models.CharField(max_length=50, blank=True, null=True, verbose_name="Largura")
    orde_esta_liga = models.CharField(max_length=50, blank=True, null=True, verbose_name="Ligação")
    orde_esta_mate = models.CharField(max_length=50, blank=True, null=True, verbose_name="Materiais")
    orde_esta_quan_mate = models.CharField(max_length=50, blank=True, null=True, verbose_name="Quantidade de Materiais")
    orde_obse = models.TextField(blank=True, null=True, verbose_name="Observações")
    orde_tens_camp = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tensão do Campo")
    orde_tens_arma = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tensão do Armadura")
    orde_corr_arma = models.CharField(max_length=50, blank=True, null=True, verbose_name="Corrente do Armadura")
    orde_corr_camp = models.CharField(max_length=50, blank=True, null=True, verbose_name="Corrente do Campo")
    orde_grau_ip = models.CharField(max_length=50, blank=True, null=True, verbose_name="Grau IP")
    orde_isol = models.CharField(max_length=50, blank=True, null=True, verbose_name="Isolamento")
    
    
    orde_data_aber = models.DateField(auto_now_add=True) 
    orde_hora_aber = models.TimeField(auto_now_add=True)
    orde_stat_orde = models.IntegerField(choices=ORDEM_STATUS_CHOICES, default=0)
    orde_seto = models.IntegerField(blank=True, null=True) 
    orde_prio = models.CharField(max_length=10, choices=Ordem_Prioridade_Choices, default="0")
    orde_prob = models.TextField(blank=True, null=True)  
    orde_defe_desc = models.TextField(blank=True, null=True)  
    orde_plac = models.CharField(max_length=20, blank=True, null=True)  
    orde_enti = models.IntegerField(blank=True, null=True)
    orde_data_fech = models.DateField(blank=True, null=True)
    orde_hora_fech = models.TimeField(blank=True, null=True)
    orde_tipo_serv = models.IntegerField(blank=True, null=True)
    orde_usua_aber = models.IntegerField(blank=True, null=True)
    orde_ulti_usua = models.CharField(max_length=100, blank=True, null=True)
    orde_ulti_alte = models.DateTimeField(blank=True, null=True)  
    orde_tota = models.DecimalField(max_digits=15, decimal_places=4, default=0)

    def calcular_total(self):
        total_pecas = sum(
            peca.peca_tota or 0 
            for peca in Ordemservicopecas.objects.filter(
                peca_empr=self.orde_empr,
                peca_fili=self.orde_fili,
                peca_orde=self.orde_nume
            )
        )
        
        total_servicos = sum(
            servico.serv_tota or 0
            for servico in Ordemservicoservicos.objects.filter(
                serv_empr=self.orde_empr,
                serv_fili=self.orde_fili,
                serv_orde=self.orde_nume
            )
        )
        
        self.orde_tota = total_pecas + total_servicos
        return self.orde_tota


    def pode_avancar_setor(self, setor_destino, banco='default'):
        """Verifica se a O.S. pode avançar para o setor destino"""
        if not self.orde_seto:
            return setor_destino == 1  # Primeira movimentação
        
        return WorkflowSetor.objects.using(banco).filter(
            wkfl_seto_orig=self.orde_seto,
            wkfl_seto_dest=setor_destino,
            wkfl_ativo=True
        ).exists()

    def obter_proximos_setores(self, banco='default'):
        """Retorna lista de setores para onde a O.S. pode avançar"""
        if not self.orde_seto:
           
            return WorkflowSetor.objects.using(banco).filter(
                wkfl_seto_orig=0, 
                wkfl_ativo=True
            ).order_by('wkfl_orde')
        
        return WorkflowSetor.objects.using(banco).filter(
            wkfl_seto_orig=self.orde_seto,
            wkfl_ativo=True
        ).order_by('wkfl_orde') 

    def avancar_setor(self, setor_destino, usuario_id,  banco='default'):
        """Avança a O.S. para o próximo setor"""
        if not self.pode_avancar_setor(setor_destino, banco):
            raise ValueError(f"Não é possível avançar do setor {self.orde_seto} para {setor_destino}")
        
        # Extrai o ID do usuário se for um objeto User
        user_id = usuario_id.pk if hasattr(usuario_id, 'pk') else usuario_id
        
        setor_origem = self.orde_seto
        self.orde_seto = setor_destino
        self.orde_ulti_usua = str(user_id)
        self.orde_ulti_alte = timezone.now()
        self.save(using=banco)
        
        # Registra no histórico
        HistoricoWorkflow.objects.using(banco).create(
            hist_empr=self.orde_empr,
            hist_fili=self.orde_fili,
            hist_orde=self.orde_nume,
            hist_seto_orig=setor_origem,
            hist_seto_dest=setor_destino,
            hist_usua=user_id,
        )
        
        return True

    def obter_historico_workflow(self, banco='default'):
        """Retorna o histórico de movimentações da O.S."""
        return HistoricoWorkflow.objects.using(banco).filter(
            hist_empr=self.orde_empr,
            hist_fili=self.orde_fili,
            hist_orde=self.orde_nume
        ).order_by('-hist_data')
    
    @property
    def itens_lista(self):
        return Ordemservicopecas.objects.filter(
        peca_empr=self.orde_empr,
        peca_fili=self.orde_fili,
        peca_orde=self.orde_nume
    )
    class Meta:
        managed = False
        db_table = 'ordemservico'
        unique_together = (('orde_empr', 'orde_fili', 'orde_nume'),)



class Ordemservicopecas(models.Model):
    peca_id = models.BigIntegerField(primary_key=True)
    peca_empr = models.IntegerField() 
    peca_fili = models.IntegerField()
    peca_orde = models.IntegerField()
    peca_codi = models.CharField(max_length=20)  
    peca_comp = models.TextField(blank=True, null=True) 
    peca_quan = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    peca_unit = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    peca_tota = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ordemservicopecas'
        unique_together = (('peca_empr', 'peca_fili', 'peca_orde', 'peca_id'),)



class Ordemservicoservicos(models.Model):
    serv_id = models.IntegerField(primary_key=True)
    serv_empr = models.IntegerField()
    serv_fili = models.IntegerField()
    serv_orde = models.IntegerField()
    serv_sequ = models.IntegerField()
    serv_codi = models.CharField(max_length=20)  
    serv_comp = models.TextField(blank=True, null=True)
    serv_quan = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    serv_unit = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    serv_tota = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ordemservicoservicos'
        unique_together = (('serv_empr', 'serv_fili', 'serv_orde', 'serv_sequ'),)


class Ordemservicoimgantes(models.Model):
    iman_id = models.AutoField(primary_key=True)
    iman_empr = models.IntegerField()
    iman_fili = models.IntegerField()
    iman_orde = models.IntegerField()
    iman_codi = models.IntegerField()
    iman_come = models.TextField(blank=True, null=True)
    iman_imag = models.BinaryField(blank=True, null=True) 
    iman_obse = models.CharField(max_length=255, blank=True, null=True)
    img_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    img_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    img_data = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'ordemservicoimgantes'


class Ordemservicoimgdurante(models.Model):
    imdu_id = models.AutoField(primary_key=True)
    imdu_empr = models.IntegerField()
    imdu_fili = models.IntegerField()
    imdu_orde = models.IntegerField()
    imdu_codi = models.IntegerField()
    imdu_come = models.TextField(blank=True, null=True)
    imdu_imag = models.BinaryField(blank=True, null=True)
    imdu_obse = models.CharField(max_length=255, blank=True, null=True)
    img_latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    img_longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    img_data = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'ordemservicoimgdurante'


class Ordemservicoimgdepois(models.Model):
    imde_id = models.AutoField(primary_key=True)
    imde_empr = models.IntegerField()
    imde_fili = models.IntegerField()
    imde_orde = models.IntegerField()
    imde_codi = models.IntegerField()
    imde_come = models.TextField(blank=True, null=True)
    imde_imag = models.BinaryField(blank=True, null=True)
    imde_obse = models.CharField(max_length=255, blank=True, null=True)
    img_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    img_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    img_data = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'ordemservicoimgdepois'
        


class OrdensEletro(models.Model):
    empresa = models.IntegerField()
    filial = models.IntegerField()
    ordem_de_servico = models.IntegerField(primary_key=True)
    cliente = models.IntegerField()
    nome_cliente = models.CharField(max_length=100)
    data_abertura = models.DateField()
    data_fim = models.DateField(null=True)
    setor = models.IntegerField()
    setor_nome = models.CharField(max_length=100)
    pecas = models.TextField()
    servicos = models.TextField()
    total_orde = models.DecimalField(max_digits=12, decimal_places=2)
    status_orde = models.CharField(max_length=50)
    responsavel = models.IntegerField()
    nome_responsavel = models.CharField(max_length=100)
    potencia = models.CharField(max_length=100)
    ultima_alteracao = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'ordenseletro'
