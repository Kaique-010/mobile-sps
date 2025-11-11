from django.db import models, transaction
from django.db.models import Q


class Centrodecustos(models.Model):
    cecu_empr = models.IntegerField(primary_key=True)
    cecu_redu = models.IntegerField()
    cecu_niv1 = models.IntegerField(blank=True, null=True)
    cecu_expa = models.CharField(max_length=60, blank=True, null=True)
    cecu_grup = models.CharField(max_length=60, blank=True, null=True)
    cecu_nive = models.IntegerField(blank=True, null=True)
    cecu_anal = models.CharField(max_length=1, blank=True, null=True)
    cecu_natu = models.CharField(max_length=2, blank=True, null=True)
    cecu_refe = models.CharField(max_length=60, blank=True, null=True)
    cecu_dati = models.DateField(blank=True, null=True)
    cecu_data = models.DateField(blank=True, null=True)
    cecu_inat = models.BooleanField(blank=True, null=True)
    cecu_data_inat = models.DateField(blank=True, null=True)
    cecu_obse = models.TextField(blank=True, null=True)
    cecu_nome = models.CharField(max_length=60, blank=True, null=True)
    cecu_dre = models.CharField(max_length=2, blank=True, null=True)
    cecu_redu_plan = models.IntegerField(blank=True, null=True)
    cecu_prod = models.CharField(max_length=20, blank=True, null=True)
    cecu_situ = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'centrodecustos'
        unique_together = (('cecu_empr', 'cecu_redu'),)

    def _next_root_code(self) -> int:
        """Próximo código de raiz (sem pai), sequencial por empresa."""
        ultimo = (
            Centrodecustos.objects
            .filter(cecu_empr=self.cecu_empr, cecu_niv1__isnull=True)
            .order_by('-cecu_redu')
            .first()
        )
        if ultimo:
            return int(ultimo.cecu_redu) + 1
        return 1

    def _next_child_code(self, parent_code: int) -> int:
        """Próximo código de filho dentro da faixa do pai (pattern: pai*1000 + n)."""
        base = int(parent_code) * 1000
        faixa_min = base + 1
        faixa_max = base + 999
        ultimo = (
            Centrodecustos.objects
            .filter(
                cecu_empr=self.cecu_empr,
                cecu_niv1=parent_code,
                cecu_redu__gte=faixa_min,
                cecu_redu__lte=faixa_max,
            )
            .order_by('-cecu_redu')
            .first()
        )
        if ultimo:
            return int(ultimo.cecu_redu) + 1
        return faixa_min

    def save(self, *args, **kwargs):
        # Lógica de geração de filhos a partir do cecu_redu, sem prefixos.
        # Define analítico/sintético: nós com filhos são 'S', folhas 'A'.
        with transaction.atomic():
            if not self.cecu_redu:
                if self.cecu_niv1:
                    # Registro filho: trava o pai para evitar corrida de geração
                    parent = (
                        Centrodecustos.objects
                        .select_for_update()
                        .filter(cecu_empr=self.cecu_empr, cecu_redu=self.cecu_niv1)
                        .first()
                    )
                    self.cecu_redu = self._next_child_code(self.cecu_niv1)
                    # Nível: herda do pai + 1 se disponível
                    if parent and parent.cecu_nive is not None:
                        self.cecu_nive = int(parent.cecu_nive) + 1
                    else:
                        self.cecu_nive = (self.cecu_nive or 0) + 1
                    # Por padrão, filho é analítico
                    if not self.cecu_anal:
                        self.cecu_anal = 'A'
                    # Marca o pai como sintético ao ganhar filhos
                    if parent and parent.cecu_anal != 'S':
                        parent.cecu_anal = 'S'
                        parent.save(update_fields=['cecu_anal'])
                else:
                    # Registro raiz: sequencial simples por empresa
                    self.cecu_redu = self._next_root_code()
                    self.cecu_nive = 1
                    if not self.cecu_anal:
                        self.cecu_anal = 'A'

            super().save(*args, **kwargs)