from django.db import models


class OrdemStatusChoices(models.TextChoices):
    ABERTA = "aberta", "Aberta"
    EM_ANDAMENTO = "andamento", "Em andamento"
    CONCLUIDA = "concluida", "Concluída"
    CANCELADA = "cancelada", "Cancelada"
    ATRASADA = "atrasada", "Atrasada"


class OrdemPrioridadeChoices(models.TextChoices):
    BAIXA = "baixa", "Baixa"
    MEDIA = "media", "Média"
    ALTA = "alta", "Alta"


class OrdensTipos(models.TextChoices):
    MANUTENCAO = "manutenca", "Manutenção"
    REVISAO = "revisao", "Revisão"
    UPGRADE = "upgrade", "Upgrade"


class Ordemservico(models.Model):
    orde_empr = models.IntegerField(primary_key=True) 
    orde_fili = models.IntegerField()
    orde_nume = models.IntegerField()  
    orde_tipo = models.CharField(max_length=20, choices=OrdensTipos.choices,default=OrdensTipos.MANUTENCAO)
    orde_data_aber = models.DateField(blank=True, null=True) 
    orde_hora_aber = models.TimeField(blank=True, null=True)
    orde_stat = models.CharField(max_length=20, choices=OrdemStatusChoices.choices, default=OrdemStatusChoices.ABERTA)
    orde_seto = models.CharField(max_length=50) 
    orde_prio = models.CharField(max_length=10, choices=OrdemPrioridadeChoices.choices, default=OrdemPrioridadeChoices.MEDIA)
    orde_prob = models.TextField(blank=True, null=True)  
    orde_defe_desc = models.TextField(blank=True, null=True)  
    orde_obse = models.TextField(blank=True, null=True) 
    orde_plac = models.CharField(max_length=20, blank=True, null=True)  
    orde_enti = models.IntegerField(blank=True, null=True)
    orde_data_fech = models.DateField(blank=True, null=True)
    orde_hora_fech = models.TimeField(blank=True, null=True)
    orde_tipo_serv = models.IntegerField(blank=True, null=True)
    orde_usua_aber = models.IntegerField(blank=True, null=True)
    orde_ulti_usua = models.CharField(max_length=100, blank=True, null=True)
    orde_ulti_alte = models.DateTimeField(blank=True, null=True)  

    class Meta:
        managed = False
        db_table = 'ordemservico'
        unique_together = (('orde_empr', 'orde_fili', 'orde_nume'),)



class Ordemservicopecas(models.Model):
    peca_id = models.AutoField(primary_key=True)
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


class Ordemservicoservicos(models.Model):
    serv_id = models.AutoField(primary_key=True)
    serv_empr = models.IntegerField()
    serv_fili = models.IntegerField()
    serv_orde = models.IntegerField()
    serv_codi = models.CharField(max_length=20)  
    serv_comp = models.TextField(blank=True, null=True)
    serv_quan = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    serv_unit = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    serv_tota = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ordemservicoservicos'


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
    img_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    img_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
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