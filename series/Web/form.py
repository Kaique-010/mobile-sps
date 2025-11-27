from django import forms
from ..models import Series

class SeriesForm(forms.ModelForm):
    class Meta:
        model = Series
        fields = '__all__'
        widgets = {
            'seri_empr': forms.HiddenInput(attrs={'placeholder': 'Digite o código da empresa'}),
            'seri_fili': forms.HiddenInput(attrs={'placeholder': 'Digite o código da filial'}),
            'seri_codi': forms.TextInput(attrs={'placeholder': 'Digite o código da série'}),
            'seri_nome': forms.Select(attrs={'placeholder': 'Digite o nome da série'}),
            'seri_docu': forms.TextInput(attrs={'placeholder': 'Digite o documento da série'}),
            'seri_obse': forms.Textarea(attrs={'placeholder': 'Digite a observação da série'}),
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
