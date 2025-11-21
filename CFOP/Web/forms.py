from django import forms
from django.conf import settings
from django.core.cache import cache
from ..models import CFOP, CFOPFiscal
import json
import urllib.request


class CFOPForm(forms.ModelForm):
    class Meta:
        model = CFOP
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
                if name == 'cfop_codi':
                    w.attrs['list'] = 'cfop-codes'
            elif isinstance(field, forms.BooleanField):
                w.attrs.setdefault('class', 'form-check-input')

    
    def clean(self):
        cleaned = super().clean()
        empr = cleaned.get('cfop_empr')
        codi = cleaned.get('cfop_codi')
        try:
            if codi:
                catalog = fetch_cfop_catalog()
                if catalog:
                    valid_set = {it['value'] for it in catalog}
                    if str(codi) not in valid_set:
                        from django.core.exceptions import ValidationError
                        raise ValidationError({'cfop_codi': 'CFOP inválido (não encontrado em fonte oficial)'})
        except Exception:
            pass
        if empr and codi:
            from django.core.exceptions import ValidationError
            from core.utils import get_licenca_db_config
            try:
                db = get_licenca_db_config(getattr(self, 'request', None))
            except Exception:
                db = None
            qs = CFOP.objects.all()
            if db:
                qs = qs.using(db)
            exists = qs.filter(cfop_empr=empr, cfop_codi=codi)
            if self.instance and self.instance.pk:
                exists = exists.exclude(cfop_empr=self.instance.cfop_empr, cfop_codi=self.instance.cfop_codi)
            if exists.exists():
                raise ValidationError({'cfop_codi': 'Código já existe para a empresa'})
        return cleaned
    
    def clean_cfop_codi(self):
        codi = self.cleaned_data["cfop_codi"]

        if not CFOPFiscal.objects.filter(cfop_codi=codi).exists():
            raise forms.ValidationError("CFOP não existe na tabela fiscal oficial.")

        return codi