from django.db import models
from Entidades.models import Entidades
from Licencas.models import Empresas



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

class Controlevisita(models.Model):
    
    SITUACAO_CHOICES = [
        (1, 'Ativo'),
        (2, 'Concluído'),
        (3, 'Cancelado'),
    ]

    ctrl_id = models.IntegerField(primary_key=True, verbose_name='ID')
    ctrl_empresa = models.ForeignKey(
        Empresas, 
        on_delete=models.DO_NOTHING, 
        db_column='ctrl_empresa',
        verbose_name='Empresa',
        blank=True, 
        null=True
    )
    ctrl_filial = models.IntegerField(verbose_name='Filial', blank=True, null=True)
    ctrl_numero = models.IntegerField(verbose_name='Número', blank=True, null=True)
    ctrl_cliente = models.ForeignKey(
        Entidades,
        on_delete=models.DO_NOTHING,
        db_column='ctrl_cliente',
        verbose_name='Cliente',
        related_name='visitas_cliente',
        blank=True,
        null=True
    )
    ctrl_data = models.DateField(verbose_name='Data da Visita', blank=True, null=True)
    ctrl_novo = models.IntegerField(verbose_name='Novo Cliente', blank=True, null=True)
    ctrl_base = models.IntegerField(verbose_name='Base', blank=True, null=True)
    ctrl_prop = models.IntegerField(verbose_name='Proposta', blank=True, null=True)
    ctrl_leva = models.IntegerField(verbose_name='Levantamento', blank=True, null=True)
    ctrl_proj = models.IntegerField(verbose_name='Projeto', blank=True, null=True)
    ctrl_etapa = models.ForeignKey(
        Etapavisita,
        on_delete=models.DO_NOTHING,
        db_column='ctrl_etapa',
        verbose_name='Etapa',
        related_name='visitas_etapa',
        blank=True,
        null=True
    )

    ctrl_vendedor = models.ForeignKey(
        Entidades,
        on_delete=models.DO_NOTHING,
        db_column='ctrl_vendedor',
        verbose_name='Vendedor',
        related_name='visitas_vendedor',
        blank=True,
        null=True
    )
    ctrl_obse = models.TextField(verbose_name='Observações', blank=True, null=True)
    ctrl_contato = models.CharField(
        max_length=50, 
        verbose_name='Contato',
        blank=True, 
        null=True
    )
    ctrl_fone = models.CharField(
        max_length=50, 
        verbose_name='Telefone',
        blank=True, 
        null=True
    )
    field_log_data = models.DateField(
        db_column='_log_data', 
        verbose_name='Data Log',
        auto_now_add=True,
        blank=True, 
        null=True
    )
    field_log_time = models.TimeField(
        db_column='_log_time', 
        verbose_name='Hora Log',
        auto_now_add=True,
        blank=True, 
        null=True
    )
    ctrl_km_inic = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        verbose_name='KM Inicial',
        blank=True, 
        null=True
    )
    ctrl_km_fina = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        verbose_name='KM Final',
        blank=True, 
        null=True
    )
    ctrl_prox_visi = models.DateField(
        verbose_name='Próxima Visita',
        blank=True, 
        null=True
    )
    ctrl_nume_orca = models.IntegerField(
        verbose_name='Número Orçamento',
        blank=True, 
        null=True
    )

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