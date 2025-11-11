from django import forms
from django.db import transaction
from .models import Centrodecustos


class CentrodecustosForm(forms.ModelForm):
    class Meta:
        model = Centrodecustos
        fields = [
            'cecu_empr', 'cecu_nome', 'cecu_niv1', 'cecu_expa', 'cecu_grup',
            'cecu_natu', 'cecu_refe', 'cecu_dati', 'cecu_data', 'cecu_inat',
            'cecu_data_inat', 'cecu_obse', 'cecu_dre', 'cecu_prod', 'cecu_situ'
        ]
        widgets = {
            'cecu_empr': forms.HiddenInput(),
            'cecu_dati': forms.DateInput(attrs={'type': 'date'}),
            'cecu_data': forms.DateInput(attrs={'type': 'date'}),
            'cecu_data_inat': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        # DB alias via request (set no mixin da view)
        self.db_alias = getattr(self.request, 'db_alias', None) if self.request else None

        # Campo cecu_empr: tentar preencher a partir da sessão/cabeçalho
        if self.request:
            empresa_id = (
                self.request.session.get('empresa_id')
                or self.request.headers.get('X-Empresa')
                or self.request.GET.get('cecu_empr')
            )
            if empresa_id:
                self.fields['cecu_empr'].initial = int(empresa_id)

        # Ajustar queryset do campo de pai para usar o banco correto
        try:
            self.fields['cecu_niv1'].widget = forms.Select()
            qs = Centrodecustos.objects.using(self.db_alias).all() if self.db_alias else Centrodecustos.objects.all()
            if self.fields['cecu_empr'].initial:
                qs = qs.filter(cecu_empr=int(self.fields['cecu_empr'].initial))
            pais = qs.order_by('cecu_redu')
            def label_for(p):
                nivel = (p.cecu_nive or 1)
                prefix = '• ' * max(0, nivel - 1)
                return f"{prefix}{p.cecu_redu} · {p.cecu_nome or ''}"
            self.fields['cecu_niv1'].choices = [('', '— raiz —')] + [
                (p.cecu_redu, label_for(p)) for p in pais
            ]
        except Exception:
            # Em caso de modelo não gerenciado, manter campo livre
            pass

    def _next_root_code(self, empresa_id: int) -> int:
        qs = Centrodecustos.objects.using(self.db_alias).filter(cecu_empr=empresa_id)
        ultimo = qs.order_by('-cecu_redu').first()
        return (int(ultimo.cecu_redu) + 1) if ultimo and ultimo.cecu_redu is not None else 1

    def _next_child_code(self, empresa_id: int, parent_code: int) -> int:
        base = int(parent_code) * 1000
        faixa_min = base + 1
        faixa_max = base + 999
        qs = Centrodecustos.objects.using(self.db_alias).filter(
            cecu_empr=empresa_id,
            cecu_niv1=parent_code,
            cecu_redu__gte=faixa_min,
            cecu_redu__lte=faixa_max,
        )
        ultimo = qs.order_by('-cecu_redu').first()
        return (int(ultimo.cecu_redu) + 1) if ultimo else faixa_min

    def save(self, commit=True):
        instance: Centrodecustos = super().save(commit=False)
        empresa_id = int(self.cleaned_data.get('cecu_empr')) if self.cleaned_data.get('cecu_empr') else None
        parent_code = self.cleaned_data.get('cecu_niv1') or None

        if not empresa_id:
            raise forms.ValidationError('Empresa (cecu_empr) é obrigatória.')

        # Gerar código no banco correto e ajustar analítico/sintético
        with transaction.atomic(using=self.db_alias):
            if not instance.cecu_redu:
                if parent_code:
                    parent = (
                        Centrodecustos.objects.using(self.db_alias)
                        .select_for_update()
                        .filter(cecu_empr=empresa_id, cecu_redu=parent_code)
                        .first()
                    )
                    instance.cecu_redu = self._next_child_code(empresa_id, parent_code)
                    instance.cecu_niv1 = parent_code
                    instance.cecu_nive = (int(parent.cecu_nive) + 1) if parent and parent.cecu_nive is not None else 2
                    instance.cecu_anal = 'A'
                    if parent and parent.cecu_anal != 'S':
                        parent.cecu_anal = 'S'
                        parent.save(using=self.db_alias, update_fields=['cecu_anal'])
                else:
                    instance.cecu_redu = self._next_root_code(empresa_id)
                    instance.cecu_nive = 1
                    instance.cecu_anal = instance.cecu_anal or 'A'

            if commit:
                instance.save(using=self.db_alias)
        return instance
