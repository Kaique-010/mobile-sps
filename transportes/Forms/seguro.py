from django import forms
from transportes.models import Cte

class CteSeguroForm(forms.ModelForm):
    class Meta:
        model = Cte
        fields = [
            'seguro_por_conta', 'seguradora', 'valor_base_seguro',
            'numero_apolice', 'numero_averbado', 'percentual_seguro', 'cte_valor_seguro'
        ]
        widgets = {
            'seguro_por_conta': forms.Select(attrs={'class': 'form-control'}),
            'seguradora': forms.NumberInput(attrs={'class': 'form-control'}),
            'valor_base_seguro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'numero_apolice': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_averbado': forms.TextInput(attrs={'class': 'form-control'}),
            'percentual_seguro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cte_valor_seguro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
