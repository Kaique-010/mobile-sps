from django import forms
from ..models import Titulospagar


class TitulosPagarForm(forms.ModelForm):
    class Meta:
        model = Titulospagar
        fields = [
            'titu_forn','titu_titu','titu_seri','titu_parc',
            'titu_emis','titu_venc','titu_valo', 'titu_cecu'
        ]
        widgets = {
            'titu_forn': forms.NumberInput(attrs={'class': 'form-control'}),
            'titu_titu': forms.TextInput(attrs={'class': 'form-control'}),
            'titu_seri': forms.TextInput(attrs={'class': 'form-control'}),
            'titu_parc': forms.TextInput(attrs={'class': 'form-control'}),
            'titu_emis': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'titu_venc': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'titu_valo': forms.NumberInput(attrs={'type': 'number', 'step': '0.01', 'class': 'form-control'}),
            'titu_cecu': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Em edição, não permitir alteração de chaves compostas para evitar conflitos de PK/UK
        if getattr(self.instance, 'pk', None):
            for f in ('titu_forn', 'titu_titu', 'titu_seri', 'titu_parc'):
                if f in self.fields:
                    self.fields[f].disabled = True
                    attrs = self.fields[f].widget.attrs
                    attrs['readonly'] = 'readonly'
