from django import forms
from ...models import Remessaretorno


class RemessaForm(forms.ModelForm):
    class Meta:
        model = Remessaretorno
        fields = [
        'banco', 'data_reme', 'nume_reme', 'valor_reme'
        ]


    widgets = {
    'data_reme': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    'valor_reme': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'})
    }
