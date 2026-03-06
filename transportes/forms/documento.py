from django import forms
from django.forms import inlineformset_factory
from transportes.models import Cte, CteDocumento

class CteDocumentoForm(forms.ModelForm):
    class Meta:
        model = CteDocumento
        fields = ['tipo_doc', 'chave_nfe']
        widgets = {
            'tipo_doc': forms.Select(attrs={'class': 'form-select'}),
            'chave_nfe': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 44, 'placeholder': 'Digite a Chave da NFe (44 dígitos)'}),
        }

CteDocumentoFormSet = inlineformset_factory(
    Cte,
    CteDocumento,
    form=CteDocumentoForm,
    extra=1,
    can_delete=True,
    fields=['tipo_doc', 'chave_nfe']
)
