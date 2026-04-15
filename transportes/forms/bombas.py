from django import forms
from transportes.models import Bombas

class BombasForm(forms.ModelForm):
    class Meta:
        model = Bombas
        fields = ('bomb_desc', 'bomb_cecu', 'bomb_forn', 'bomb_obse')
        widgets = {
            'bomb_desc': forms.TextInput(attrs={'class': 'form-control'}),
            'bomb_cecu': forms.HiddenInput(attrs={'class': 'form-control'}),
            'bomb_forn': forms.HiddenInput(attrs={'class': 'form-control'}),
            'bomb_obse': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'bomb_desc': 'Descrição Bomba',
            'bomb_cecu': 'Centro de custo da Bomba',
            'bomb_forn': 'Fornecedor da Bomba',
            'bomb_obse': 'Observação Bomba',
        }
