from django import forms
from ...models import Boleto


class BoletoForm(forms.ModelForm):
    class Meta:
        model = Boleto
        fields = [
        'bole_empr', 'bole_fili', 'bole_soci',
        'bole_titu', 'bole_seri', 'bole_parc',
        'bole_emis', 'bole_venc', 'bole_valo',
        'bole_noss', 'bole_linh_digi'
        ]   


    widgets = {
    'bole_emis': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    'bole_venc': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    'bole_valo': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
    }