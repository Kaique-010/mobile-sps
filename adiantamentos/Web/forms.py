from django import forms
from ..models import Adiantamentos
from Entidades.models import Entidades


class AdiantamentosForm(forms.ModelForm):
    class Meta:
        model = Adiantamentos
        fields = [
            'adia_tipo',
            'adia_valo',
            'adia_enti',
            'adia_docu',
            'adia_seri',
            'adia_obse',
            'adia_banc',
            'adia_ctrl_banc',
        ]
        widgets = {
            'adia_tipo': forms.Select(attrs={'class': 'form-control'}),
            'adia_valo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'adia_enti': forms.NumberInput(attrs={'class': 'form-control'}),
            'adia_docu': forms.NumberInput(attrs={'class': 'form-control'}),
            'adia_seri': forms.TextInput(attrs={'class': 'form-control'}),
            'adia_obse': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'adia_banc': forms.NumberInput(attrs={'class': 'form-control'}),
            'adia_ctrl_banc': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'adia_enti': 'Entidade',
            'adia_docu': 'Documento',
            'adia_seri': 'Série',
            'adia_valo': 'Valor Adiantamento',
            'adia_obse': 'Observação',
            'adia_banc': 'Banco',
            'adia_ctrl_banc': 'Controle Bancário',
            'adia_tipo': 'Tipo Adiantamento',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['adia_enti'].queryset = Entidades.objects.all().order_by('entidade_nome')