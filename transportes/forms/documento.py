from django import forms
from django.forms import inlineformset_factory
from transportes.models import Cte, CteDocumento
import re

class CteDocumentoForm(forms.ModelForm):
    class Meta:
        model = CteDocumento
        fields = ['tipo_doc', 'chave_nfe']
        widgets = {
            'tipo_doc': forms.Select(attrs={'class': 'form-select'}),
            'chave_nfe': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 44, 'placeholder': 'Digite a Chave da NFe (44 dígitos)'}),
        }

    def clean_chave_nfe(self):
        raw = (self.cleaned_data.get("chave_nfe") or "").strip()
        if not raw:
            return None

        chave = re.sub(r"\D", "", raw)
        if not chave.isdigit():
            raise forms.ValidationError("Informe apenas números na chave da NF-e.")
        if len(chave) != 44:
            raise forms.ValidationError("A chave da NF-e deve ter exatamente 44 dígitos.")

        soma = 0
        peso = 2
        for digito in reversed(chave[:43]):
            soma += int(digito) * peso
            peso += 1
            if peso > 9:
                peso = 2
        resto = soma % 11
        dv_calc = 0 if resto < 2 else 11 - resto

        if str(dv_calc) != chave[-1]:
            raise forms.ValidationError("Chave da NF-e com DV inválido.")

        return chave

CteDocumentoFormSet = inlineformset_factory(
    Cte,
    CteDocumento,
    form=CteDocumentoForm,
    extra=1,
    can_delete=True,
    fields=['tipo_doc', 'chave_nfe']
)
