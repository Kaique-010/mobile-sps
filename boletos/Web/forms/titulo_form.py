from django import forms
from ...models import Titulosreceber


class TituloReceberForm(forms.ModelForm):
    class Meta:
        model = Titulosreceber
        fields = [
        'titu_empr', 'titu_fili', 'titu_clie',
        'titu_titu', 'titu_seri', 'titu_parc',
        'titu_emis', 'titu_venc', 'titu_valo'
        ]


        widgets = {
        'titu_emis': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        'titu_venc': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        'titu_valo': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
        }