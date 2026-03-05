from django import forms
from transportes.models import Cte

class CteTipoForm(forms.ModelForm):
    class Meta:
        model = Cte
        fields = [
            'tomador_servico', 'tipo_servico', 'tipo_cte', 'forma_emissao',
            'tipo_frete', 'redespacho', 'subcontratado', 'outro_tomador', 'transportadora'
        ]
        widgets = {
            'tomador_servico': forms.RadioSelect(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'tipo_servico': forms.RadioSelect(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'tipo_cte': forms.RadioSelect(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'forma_emissao': forms.RadioSelect(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'tipo_frete': forms.RadioSelect(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'redespacho': forms.NumberInput(attrs={'class': 'form-control'}),
            'subcontratado': forms.NumberInput(attrs={'class': 'form-control'}),
            'outro_tomador': forms.NumberInput(attrs={'class': 'form-control'}),
            'transportadora': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
