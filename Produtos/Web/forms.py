
from django import forms
from Produtos.models import Ncm
from Produtos.models import NcmAliquota


class NcmAliquotaForm(forms.ModelForm):
    class Meta:
        model = NcmAliquota
        fields = [
            "nali_ncm",
            "nali_aliq_ipi",
            "nali_aliq_pis",
            "nali_aliq_cofins",
            "nali_aliq_cbs",
            "nali_aliq_ibs",
        ]

        widgets = {
            "nali_ncm": forms.TextInput(attrs={"class": "form-control", "placeholder": "Código NCM", "list": "ncm-codes"}),
            "nali_aliq_ipi": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "nali_aliq_pis": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "nali_aliq_cofins": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "nali_aliq_cbs": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "nali_aliq_ibs": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        self.database = kwargs.pop('database', 'default')
        super().__init__(*args, **kwargs)
        try:
            if 'nali_ncm' in self.fields:
                self.fields['nali_ncm'].queryset = Ncm.objects.using(self.database).all().order_by('ncm_codi')
        except Exception:
            pass

    def clean_nali_ncm(self):
        value = self.cleaned_data.get('nali_ncm')
        if isinstance(value, Ncm):
            return value
        codigo = str(value or '').strip()
        if not codigo:
            raise forms.ValidationError('Informe o NCM')
        obj = Ncm.objects.using(self.database).filter(ncm_codi=codigo).first()
        if not obj:
            raise forms.ValidationError('NCM inválido')
        return obj


class NcmForm(forms.ModelForm):
    class Meta:
        model = Ncm
        fields = [
            "ncm_codi",
            "ncm_desc",
        ]
        widgets = {
            "ncm_codi": forms.TextInput(attrs={"class": "form-control", "placeholder": "Código NCM"}),
            "ncm_desc": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Descrição"}),
        }

    def clean_ncm_codi(self):
        codigo = (self.cleaned_data.get("ncm_codi") or "").strip()
        if not codigo:
            raise forms.ValidationError("Informe o código NCM.")
        if len(codigo) > 10:
            raise forms.ValidationError("Código NCM deve ter até 10 caracteres.")
        return codigo
