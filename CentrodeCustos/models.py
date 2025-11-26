from django.db import models, transaction, DEFAULT_DB_ALIAS
from django.db.models import Q
from django.conf import settings


class Centrodecustos(models.Model):
    cecu_empr = models.IntegerField()
    cecu_redu = models.IntegerField(primary_key=True)
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

    @staticmethod
    def _mask_digits() -> int:
        return int(getattr(settings, 'CENTROSDECUSTOS_MASK_DIGITS', 3))

    @staticmethod
    def _mask_levels() -> int:
        return int(getattr(settings, 'CENTROSDECUSTOS_MASK_LEVELS', 4))

    @classmethod
    def _mask_base(cls) -> int:
        return 10 ** cls._mask_digits()

    def _format_expa(self, code: int) -> str:
        s = str(int(code))
        if len(s) <= 1:
            return s
        if len(s) <= 3:
            return f"{s[:-2]}.{s[-2:]}"
        return f"{s[:-5]}.{s[-5:-3]}.{s[-3:]}"

    def _next_root_code(self, db_alias: str | None = None) -> int:
        qs = (
            Centrodecustos.objects.using(db_alias) if db_alias else Centrodecustos.objects
        )
        existing = list(
            qs.filter(cecu_empr=self.cecu_empr, cecu_niv1__isnull=True)
              .order_by('cecu_redu')
              .values_list('cecu_redu', flat=True)
        )
        expected = 1
        for code in existing:
            code = int(code)
            if code != expected:
                break
            expected += 1
        return expected

    def _next_child_code(self, parent_code: int, db_alias: str | None = None) -> int:
        base_unit = self._mask_base()
        base = int(parent_code) * base_unit
        faixa_min = base + 1
        faixa_max = base + (base_unit - 1)
        qs = (
            Centrodecustos.objects.using(db_alias) if db_alias else Centrodecustos.objects
        )
        existing = list(
            qs.filter(
                cecu_empr=self.cecu_empr,
                cecu_niv1=parent_code,
                cecu_redu__gte=faixa_min,
                cecu_redu__lte=faixa_max,
            )
            .order_by('cecu_redu')
            .values_list('cecu_redu', flat=True)
        )
        # Procura o primeiro "buraco" na faixa pela máscara
        expected = faixa_min
        for code in existing:
            code = int(code)
            if code != expected:
                break
            expected += 1
        return expected

    def save(self, *args, **kwargs):
        db_alias = kwargs.get('using') or DEFAULT_DB_ALIAS
        with transaction.atomic(using=db_alias):
            if not self.cecu_redu:
                # Sequência global por empresa
                from django.db.models import Max
                max_redu = (
                    (Centrodecustos.objects.using(db_alias) if db_alias else Centrodecustos.objects)
                    .filter(cecu_empr=self.cecu_empr)
                    .aggregate(m=Max('cecu_redu'))
                    .get('m')
                )
                self.cecu_redu = (int(max_redu) + 1) if max_redu else 1
                # Definir nível com base no pai, quando houver
                if self.cecu_niv1:
                    parent = (
                        (Centrodecustos.objects.using(db_alias) if db_alias else Centrodecustos.objects)
                        .filter(cecu_empr=self.cecu_empr, cecu_redu=self.cecu_niv1)
                        .first()
                    )
                    if parent and parent.cecu_nive is not None:
                        self.cecu_nive = int(parent.cecu_nive) + 1
                    else:
                        self.cecu_nive = (self.cecu_nive or 0) + 1
                    if not self.cecu_anal:
                        self.cecu_anal = 'A' if (self.cecu_nive == 3) else 'S'
                    if parent and parent.cecu_anal != 'S':
                        parent.cecu_anal = 'S'
                        parent.save(update_fields=['cecu_anal'], using=db_alias)
                else:
                    self.cecu_nive = 1
                    if not self.cecu_anal:
                        self.cecu_anal = 'A' if (self.cecu_nive == 3) else 'S'

            if not self.cecu_expa:
                self.cecu_expa = self._format_expa(self.cecu_redu)
            parts = (self.cecu_expa or '').split('.')
            if len(parts) >= 2:
                self.cecu_grup = parts[0] + '.' + parts[1]
            elif parts:
                self.cecu_grup = parts[0]
            else:
                self.cecu_grup = None

            super().save(*args, **kwargs)
   
