from django import forms
from transportes.models import Cte

class CteRotaForm(forms.ModelForm):
    class Meta:
        model = Cte
        fields = [
            'cidade_coleta', 'cidade_entrega', 'pedagio', 'peso_total',
            'tarifa', 'frete_peso', 'frete_valor', 'outras_observacoes'
        ]
        widgets = {
            'cidade_coleta': forms.NumberInput(attrs={'class': 'form-control'}),
            'cidade_entrega': forms.NumberInput(attrs={'class': 'form-control'}),
            'pedagio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'peso_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'tarifa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'frete_peso': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'frete_valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'outras_observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
