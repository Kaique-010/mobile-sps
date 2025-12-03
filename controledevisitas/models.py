from django.db import models
from Entidades.models import Entidades
from Licencas.models import Empresas, Filiais



class Etapavisita(models.Model):
    etap_id = models.IntegerField(primary_key=True)
    etap_nume = models.IntegerField()
    etap_descricao = models.CharField(max_length=50, blank=True, null=True)
    etap_empr = models.ForeignKey(Empresas, models.DO_NOTHING, db_column='etap_empr')
    etap_obse = models.CharField(max_length=200, blank=True, null=True)


    class Meta:
        managed = False
        db_table = 'etapavisita'
        unique_together = (('etap_empr', 'etap_nume'), ('etap_id', 'etap_empr'),)
        verbose_name = 'Etapa de Visita'
        verbose_name_plural = 'Etapas de Visitas'
        db_table = 'etapavisita'
        unique_together = (('etap_empr', 'etap_nume'), ('etap_id', 'etap_empr'),)
    
    def __str__(self):
        return self.etap_descricao


class Controlevisita(models.Model):
    
    SITUACAO_CHOICES = [
        (1, 'Ativo'),
        (2, 'Concluído'),
        (3, 'Cancelado'),
    ]

    ctrl_id = models.IntegerField(primary_key=True, verbose_name='ID')
    ctrl_empresa = models.ForeignKey(Empresas,on_delete=models.DO_NOTHING,db_column='ctrl_empresa',verbose_name='Empresa',blank=True,null=True)
    ctrl_filial = models.IntegerField(db_column='ctrl_filial', verbose_name='Filial', blank=True, null=True)
    ctrl_numero = models.IntegerField(verbose_name='Número', blank=True, null=True)
    ctrl_cliente = models.ForeignKey(Entidades,on_delete=models.DO_NOTHING,db_column='ctrl_cliente',verbose_name='Cliente',related_name='visitas_cliente',blank=True,null=True)
    ctrl_data = models.DateField(verbose_name='Data da Visita', blank=True, null=True)
    ctrl_novo = models.IntegerField(verbose_name='Novo Cliente', blank=True, null=True)
    ctrl_base = models.IntegerField(verbose_name='Base', blank=True, null=True)
    ctrl_prop = models.IntegerField(verbose_name='Proposta', blank=True, null=True)
    ctrl_leva = models.IntegerField(verbose_name='Levantamento', blank=True, null=True)
    ctrl_proj = models.IntegerField(verbose_name='Projeto', blank=True, null=True)
    ctrl_etapa = models.ForeignKey(Etapavisita,on_delete=models.DO_NOTHING,db_column='ctrl_etapa',verbose_name='Etapa',related_name='visitas_etapa',blank=True,null=True)
    ctrl_vendedor = models.ForeignKey(Entidades,on_delete=models.DO_NOTHING,db_column='ctrl_vendedor',verbose_name='Vendedor',related_name='visitas_vendedor',blank=True,null=True) 
    ctrl_obse = models.TextField(verbose_name='Observações', blank=True, null=True)
    ctrl_contato = models.CharField(max_length=50,verbose_name='Contato',blank=True,null=True)
    ctrl_fone = models.CharField(max_length=50, verbose_name='Telefone', blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data',verbose_name='Data Log',auto_now_add=True,blank=True,null=True)
    field_log_time = models.TimeField(db_column='_log_time',verbose_name='Hora Log',auto_now_add=True,blank=True,null=True)
    ctrl_km_inic = models.DecimalField(max_digits=15,decimal_places=2, verbose_name='KM Inicial',blank=True,null=True)
    ctrl_km_fina = models.DecimalField(max_digits=15,decimal_places=2,verbose_name='KM Final',blank=True,null=True)
    ctrl_prox_visi = models.DateField(verbose_name='Próxima Visita', blank=True,null=True)
    ctrl_nume_orca = models.IntegerField(verbose_name='Número Orçamento',blank=True,null=True)

    class Meta:
        managed = False
        db_table = 'controlevisita'
        unique_together = (('ctrl_empresa', 'ctrl_filial', 'ctrl_numero'),)
        verbose_name = 'Controle de Visita'
        verbose_name_plural = 'Controles de Visitas'

    def __str__(self):
        return f"Visita {self.ctrl_numero} - {self.ctrl_data}"

    @property
    def km_percorrido(self):
        if self.ctrl_km_inic and self.ctrl_km_fina:
            return self.ctrl_km_fina - self.ctrl_km_inic
        return None
    
    def get_ctrl_etapa_display(self):
        if self.ctrl_etapa:
            return self.ctrl_etapa.etap_descricao
        return None
    


class ItensVisita(models.Model):
    item_id = models.AutoField(primary_key=True)
    item_empr = models.ForeignKey(Empresas, on_delete=models.CASCADE, db_column='item_empr')
    item_fili = models.IntegerField(db_column='item_fili')
    item_visita = models.ForeignKey(Controlevisita, on_delete=models.CASCADE, related_name="itens_visita_id")
    item_prod = models.CharField(max_length=60, verbose_name='Código do Produto')
    item_desc_prod = models.TextField(blank=True, null=True, verbose_name='Descrição do Produto')
    item_quan = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True, verbose_name='Quantidade')
    item_unit = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True, verbose_name='Valor Unitário')
    item_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Valor Total')
    item_desc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Desconto')
    item_unli = models.CharField(max_length=10, blank=True, null=True, verbose_name='Unidade')
    item_data = models.DateField(auto_now_add=True, verbose_name='Data')
    item_obse = models.TextField(blank=True, null=True, verbose_name='Observações')
    
    # Campos específicos para pisos
    item_m2 = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name='Metragem (m²)')
    item_nome_ambi = models.CharField(max_length=100, blank=True, null=True, verbose_name='Nome do Ambiente')
    item_queb = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='% Quebra', default=10)
    item_caix = models.IntegerField(blank=True, null=True, verbose_name='Caixas Necessárias')
    item_tipo_calculo = models.CharField(
        max_length=10, 
        choices=[('normal', 'Normal'), ('pisos', 'Pisos')], 
        default='normal', 
        verbose_name='Tipo de Cálculo'
    )

    class Meta:
        db_table = "itensvisita"
        unique_together = (("item_empr", "item_fili", "item_visita", "item_prod"),)
        verbose_name = 'Item de Visita'
        verbose_name_plural = 'Itens de Visita'

    def save(self, *args, **kwargs):
        # Calcular total automaticamente
        if self.item_quan and self.item_unit:
            total_bruto = self.item_quan * self.item_unit
            desconto = self.item_desc or 0
            self.item_tota = total_bruto - desconto
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_prod} ({self.item_quan})"
