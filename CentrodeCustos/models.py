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
        base = self._mask_base()
        digits = self._mask_digits()
        parts = []
        temp = int(code)
        while temp >= base:
            parts.append(temp % base)
            temp //= base
        parts.append(temp)
        parts = list(reversed(parts))
        formatted = [str(parts[0])]
        for p in parts[1:]:
            formatted.append(str(p).zfill(digits))
        return '.'.join(formatted)

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
                if self.cecu_niv1:
                    parent = (
                        (Centrodecustos.objects.using(db_alias) if db_alias else Centrodecustos.objects)
                        .select_for_update()
                        .filter(cecu_empr=self.cecu_empr, cecu_redu=self.cecu_niv1)
                        .first()
                    )
                    if parent and parent.cecu_anal not in ('S', None):
                        from django.core.exceptions import ValidationError
                        raise ValidationError('Conta analítica deve ter pai sintético.')
                    next_code = self._next_child_code(self.cecu_niv1, db_alias=db_alias)
                    base_unit = self._mask_base()
                    if next_code > int(self.cecu_niv1) * base_unit + (base_unit - 1):
                        from django.core.exceptions import ValidationError
                        raise ValidationError('Limite numérico do nível excedido.')
                    self.cecu_redu = next_code
                    if parent and parent.cecu_nive is not None:
                        self.cecu_nive = int(parent.cecu_nive) + 1
                    else:
                        self.cecu_nive = (self.cecu_nive or 0) + 1
                    if not self.cecu_anal:
                        self.cecu_anal = 'A'
                    if parent and parent.cecu_anal != 'S':
                        parent.cecu_anal = 'S'
                        parent.save(update_fields=['cecu_anal'], using=db_alias)
                else:
                    self.cecu_redu = self._next_root_code(db_alias=db_alias)
                    self.cecu_nive = 1
                    if not self.cecu_anal:
                        self.cecu_anal = 'A'

            self.cecu_expa = self._format_expa(self.cecu_redu)
            self.cecu_grup = self.cecu_expa

            super().save(*args, **kwargs)

            if self.cecu_anal == 'S':
                base_unit = self._mask_base()
                faixa_min = int(self.cecu_redu) * base_unit + 1
                faixa_max = int(self.cecu_redu) * base_unit + (base_unit - 1)
                tem_sintetico_filho = (
                    (Centrodecustos.objects.using(db_alias) if db_alias else Centrodecustos.objects)
                    .filter(
                        cecu_empr=self.cecu_empr,
                        cecu_niv1=self.cecu_redu,
                        cecu_anal='S',
                        cecu_redu__gte=faixa_min,
                        cecu_redu__lte=faixa_max,
                    )
                    .exists()
                )
                tem_qualquer_filho = (
                    (Centrodecustos.objects.using(db_alias) if db_alias else Centrodecustos.objects)
                    .filter(
                        cecu_empr=self.cecu_empr,
                        cecu_niv1=self.cecu_redu,
                        cecu_redu__gte=faixa_min,
                        cecu_redu__lte=faixa_max,
                    )
                    .exists()
                )
                if not tem_sintetico_filho and not tem_qualquer_filho:
                    filho = Centrodecustos(
                        cecu_empr=self.cecu_empr,
                        cecu_niv1=self.cecu_redu,
                        cecu_nome=self.cecu_nome,
                        cecu_anal='A',
                    )
                    filho.save(using=db_alias)
   
