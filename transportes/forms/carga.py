from django import forms
from transportes.models import Cte

class CteCargaForm(forms.ModelForm):
    class Meta:
        model = Cte
        fields = [
            'total_mercadoria', 'produto_predominante', 'unidade_medida',
            'tipo_medida', 'numero_contrato', 'numero_lacre',
            'data_previsao_entrega', 'ncm', 'total_peso'
        ]
        widgets = {
            'total_mercadoria': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'produto_predominante': forms.TextInput(attrs={'class': 'form-control'}),
            'unidade_medida': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_medida': forms.Select(attrs={'class': 'form-control'}),
            'numero_contrato': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_lacre': forms.TextInput(attrs={'class': 'form-control'}),
            'data_previsao_entrega': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'ncm': forms.TextInput(attrs={'class': 'form-control'}),
            'total_peso': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
        }
