from django import forms
from ..models import Titulosreceber


class TitulosReceberForm(forms.ModelForm):
    class Meta:
        model = Titulosreceber
        fields = ['titu_clie', 'titu_seri', 'titu_parc', 'titu_valo', 'titu_emis', 'titu_venc', 'titu_titu', 'titu_cecu']
        widgets = {
            'titu_clie': forms.NumberInput(attrs={'class': 'form-control'}),
            'titu_seri': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 5}),
            'titu_parc': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 3}),
            'titu_valo': forms.NumberInput(attrs={'type': 'number', 'step': '0.01', 'class': 'form-control'}),
            'titu_emis': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'titu_venc': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'titu_titu': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 13}),
            'titu_cecu': forms.HiddenInput(),
        }
