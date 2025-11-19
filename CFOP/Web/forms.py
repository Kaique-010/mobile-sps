from django import forms
from ..models import Cfop, CST_ICMS_CHOICES, CST_PIS_CHOICES, CST_COFINS_CHOICES, CST_IPI_CHOICES

class CfopForm(forms.ModelForm):
    class Meta:
        model = Cfop
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        database = kwargs.pop('database', 'default')
        empresa_id = kwargs.pop('empresa_id', None)
        super().__init__(*args, **kwargs)

        if empresa_id is not None:
            self.fields['cfop_empr'].initial = empresa_id
        self.fields['cfop_empr'].widget = forms.HiddenInput()

        for name, field in self.fields.items():
            w = getattr(field, 'widget', None)
            if not w:
                continue
            if isinstance(field, (forms.DecimalField, forms.IntegerField)):
                w.attrs.setdefault('class', 'form-control text-end')
                w.attrs.setdefault('step', '0.01')
            elif isinstance(field, forms.CharField):
                w.attrs.setdefault('class', 'form-control')
            elif isinstance(field, forms.BooleanField):
                w.attrs.setdefault('class', 'form-check-input')

        if 'cfop_trib_cst_icms' in self.fields:
            self.fields['cfop_trib_cst_icms'].widget = forms.Select(choices=CST_ICMS_CHOICES, attrs={'class': 'form-select'})
        if 'cfop_trib_cst_pis' in self.fields:
            self.fields['cfop_trib_cst_pis'].widget = forms.Select(choices=CST_PIS_CHOICES, attrs={'class': 'form-select'})
        if 'cfop_trib_cst_cofins' in self.fields:
            self.fields['cfop_trib_cst_cofins'].widget = forms.Select(choices=CST_COFINS_CHOICES, attrs={'class': 'form-select'})
        if 'cfop_trib_ipi_trib' in self.fields:
            self.fields['cfop_trib_ipi_trib'].widget = forms.Select(choices=CST_IPI_CHOICES, attrs={'class': 'form-select'})
        if 'cfop_trib_ipi_nao_trib' in self.fields:
            self.fields['cfop_trib_ipi_nao_trib'].widget = forms.Select(choices=CST_IPI_CHOICES, attrs={'class': 'form-select'})

    def clean(self):
        cleaned = super().clean()
        empr = cleaned.get('cfop_empr')
        codi = cleaned.get('cfop_codi')
        if empr and codi:
            from django.core.exceptions import ValidationError
            from core.utils import get_licenca_db_config
            try:
                db = get_licenca_db_config(getattr(self, 'request', None))
            except Exception:
                db = None
            qs = Cfop.objects.all()
            if db:
                qs = qs.using(db)
            exists = qs.filter(cfop_empr=empr, cfop_codi=codi)
            if self.instance and self.instance.pk:
                exists = exists.exclude(cfop_empr=self.instance.cfop_empr, cfop_codi=self.instance.cfop_codi)
            if exists.exists():
                raise ValidationError({'cfop_codi': 'Código já existe para a empresa'})
        return cleaned