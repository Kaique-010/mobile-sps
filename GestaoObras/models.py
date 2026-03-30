from django.db import models


class Obra(models.Model):
    STATUS_CHOICES = [
        ("PL", "Planejada"),
        ("EA", "Em andamento"),
        ("PA", "Paralisada"),
        ("CO", "Concluída"),
        ("CA", "Cancelada"),
    ]

    obra_empr = models.IntegerField()
    obra_fili = models.IntegerField()
    obra_codi = models.IntegerField()
    obra_nome = models.CharField(max_length=150)
    obra_desc = models.TextField(blank=True, null=True)
    obra_clie = models.IntegerField(db_column="obra_clie")
    obra_resp = models.IntegerField(db_column="obra_resp", blank=True, null=True)
    obra_dini = models.DateField()
    obra_dpre = models.DateField(blank=True, null=True)
    obra_dfim = models.DateField(blank=True, null=True)
    obra_orca = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    obra_cust = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    obra_stat = models.CharField(max_length=2, choices=STATUS_CHOICES, default="PL")
    obra_ativ = models.BooleanField(default=True)
    obra_crea = models.DateTimeField(auto_now_add=True)
    obra_alte = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gestao_obras"
        ordering = ("obra_codi",)
        unique_together = (("obra_empr", "obra_fili", "obra_codi"),)

    def __str__(self):
        return f"{self.obra_codi} - {self.obra_nome}"


class ObraEtapa(models.Model):
    SITUACAO_CHOICES = [
        ("PE", "Pendente"),
        ("EA", "Em andamento"),
        ("FI", "Finalizada"),
    ]

    etap_empr = models.IntegerField()
    etap_fili = models.IntegerField()
    etap_codi = models.IntegerField()
    etap_obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="etapas")
    etap_nome = models.CharField(max_length=120)
    etap_desc = models.TextField(blank=True, null=True)
    etap_orde = models.PositiveIntegerField(default=1)
    etap_dinp = models.DateField(blank=True, null=True)
    etap_dfip = models.DateField(blank=True, null=True)
    etap_dinr = models.DateField(blank=True, null=True)
    etap_dfir = models.DateField(blank=True, null=True)
    etap_situ = models.CharField(max_length=2, choices=SITUACAO_CHOICES, default="PE")
    etap_perc = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    etap_crea = models.DateTimeField(auto_now_add=True)
    etap_alte = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gestao_obras_etapas"
        ordering = ("etap_obra", "etap_orde")
        unique_together = (("etap_empr", "etap_fili", "etap_codi"),)
    
    def __str__(self):
        return f"{self.etap_codi} - {self.etap_nome}"


class ObraMaterialMovimento(models.Model):
    TIPO_CHOICES = [
        ("EN", "Entrada"),
        ("SA", "Saída"),
    ]

    movm_empr = models.IntegerField()
    movm_fili = models.IntegerField()
    movm_codi = models.IntegerField()
    movm_obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="movimentos_materiais")
    movm_etap = models.ForeignKey(
        ObraEtapa,
        on_delete=models.SET_NULL,
        related_name="movimentos_materiais",
        blank=True,
        null=True,
    )
    movm_tipo = models.CharField(max_length=2, choices=TIPO_CHOICES)
    movm_prod = models.CharField(max_length=20)
    movm_desc = models.CharField(max_length=255)
    movm_quan = models.DecimalField(max_digits=15, decimal_places=3)
    movm_unid = models.CharField(max_length=6, default="UN")
    movm_cuni = models.DecimalField(max_digits=15, decimal_places=6, default=0)
    movm_data = models.DateField()
    movm_docu = models.CharField(max_length=30, blank=True, null=True)
    movm_obse = models.TextField(blank=True, null=True)
    movm_crea = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gestao_obras_movimentos_materiais"
        ordering = ("-movm_data", "-movm_codi")
        unique_together = (("movm_empr", "movm_fili", "movm_codi"),)
    
    def __str__(self):
        return f"{self.movm_codi} - {self.movm_prod}"


class ObraLancamentoFinanceiro(models.Model):
    TIPO_CHOICES = [
        ("RE", "Receita"),
        ("DE", "Despesa"),
    ]

    lfin_empr = models.IntegerField()
    lfin_fili = models.IntegerField()
    lfin_codi = models.IntegerField()
    lfin_obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="lancamentos_financeiros")
    lfin_etap = models.ForeignKey(
        ObraEtapa,
        on_delete=models.SET_NULL,
        related_name="lancamentos_financeiros",
        blank=True,
        null=True,
    )
    lfin_tipo = models.CharField(max_length=2, choices=TIPO_CHOICES)
    lfin_cate = models.CharField(max_length=80)
    lfin_desc = models.CharField(max_length=255)
    lfin_valo = models.DecimalField(max_digits=15, decimal_places=2)
    lfin_dcom = models.DateField()
    lfin_dpag = models.DateField(blank=True, null=True)
    lfin_obse = models.TextField(blank=True, null=True)
    lfin_crea = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gestao_obras_lancamentos_financeiros"
        ordering = ("-lfin_dcom", "-lfin_codi")
        unique_together = (("lfin_empr", "lfin_fili", "lfin_codi"),)
    
    def __str__(self):
        return f"{self.lfin_codi} - {self.lfin_cate}"


class ObraProcesso(models.Model):
    PRIORIDADE_CHOICES = [
        ("BA", "Baixa"),
        ("ME", "Média"),
        ("AL", "Alta"),
        ("CR", "Crítica"),
    ]
    STATUS_CHOICES = [
        ("AB", "Aberto"),
        ("EA", "Em andamento"),
        ("CO", "Concluído"),
        ("BL", "Bloqueado"),
    ]

    proc_empr = models.IntegerField()
    proc_fili = models.IntegerField()
    proc_codi = models.IntegerField()
    proc_obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="processos")
    proc_etap = models.ForeignKey(
        ObraEtapa,
        on_delete=models.SET_NULL,
        related_name="processos",
        blank=True,
        null=True,
    )
    proc_titu = models.CharField(max_length=120)
    proc_desc = models.TextField(blank=True, null=True)
    proc_resp = models.IntegerField(blank=True, null=True)
    proc_dlim = models.DateField(blank=True, null=True)
    proc_prio = models.CharField(max_length=2, choices=PRIORIDADE_CHOICES, default="ME")
    proc_stat = models.CharField(max_length=2, choices=STATUS_CHOICES, default="AB")
    proc_crea = models.DateTimeField(auto_now_add=True)
    proc_alte = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gestao_obras_processos"
        ordering = ("-proc_codi",)
        unique_together = (("proc_empr", "proc_fili", "proc_codi"),)
    
    def __str__(self):
        return f"{self.proc_codi} - {self.proc_titu}"
