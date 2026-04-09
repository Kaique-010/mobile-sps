from django import forms

from TrocasDevolucoes.models import TrocaDevolucao


class TrocaDevolucaoForm(forms.ModelForm):
    class Meta:
        model = TrocaDevolucao
        fields = [
            'tdvl_empr', 'tdvl_fili', 'tdvl_pdor', 'tdvl_clie', 'tdvl_vend',
            'tdvl_data', 'tdvl_tipo', 'tdvl_stat', 'tdvl_tode', 'tdvl_tore',
            'tdvl_safi', 'tdvl_obse'
        ]
        widgets = {
            'tdvl_data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tdvl_tipo': forms.Select(attrs={'class': 'form-select'}),
            'tdvl_stat': forms.Select(attrs={'class': 'form-select'}),
            'tdvl_empr': forms.NumberInput(attrs={'class': 'form-control'}),
            'tdvl_fili': forms.NumberInput(attrs={'class': 'form-control'}),
            'tdvl_pdor': forms.NumberInput(attrs={'class': 'form-control'}),
            'tdvl_clie': forms.TextInput(attrs={'class': 'form-control'}),
            'tdvl_vend': forms.TextInput(attrs={'class': 'form-control'}),
            'tdvl_tode': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tdvl_tore': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tdvl_safi': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tdvl_obse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
