from django import forms
from django.core.exceptions import ValidationError
from ..models import Series

class SeriesForm(forms.ModelForm):
    class Meta:
        model = Series
        fields = '__all__'
        widgets = {
            'seri_codi': forms.TextInput(attrs={'placeholder': 'Digite o código da série, ex: 001', 'class': 'form-control'}),
            'seri_nome': forms.Select(attrs={'placeholder': 'Digite o nome da série', 'class': 'form-control'}),
            'seri_docu': forms.TextInput(attrs={'placeholder': 'Digite o documento da série, para inciar do 1, insrira 0', 'class': 'form-control'}),
        }
        
        labels = {
            'seri_empr': 'Empresa',
            'seri_fili': 'Filial',
            'seri_codi': 'Código',
            'seri_nome': 'Nome',
            'seri_docu': 'Documento',
            'seri_obse': 'Observação',
            'seri_nume_livr': 'Número Livre',
        }

    def __init__(self, *args, empresa_id=None, filial_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if 'seri_empr' in self.fields:
            if empresa_id is not None:
                self.fields['seri_empr'].initial = empresa_id
            self.fields['seri_empr'].widget = forms.HiddenInput()
        if 'seri_fili' in self.fields:
            if filial_id is not None:
                self.fields['seri_fili'].initial = filial_id
            self.fields['seri_fili'].widget = forms.HiddenInput()

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('seri_nome')
        codi = cleaned.get('seri_codi') or ''
        if tipo == 'PR':
            c = str(codi).zfill(3)
            if not c.isdigit() or not (920 <= int(c) <= 969):
                raise ValidationError({'seri_codi': 'Para Produtor Rural use série entre 920 e 969.'})
            cleaned['seri_codi'] = c
        return cleaned
