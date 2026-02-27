from django import forms
from Entidades.models import Entidades
from django.db.models import Q

class NotaManualForm(forms.Form):
    fornecedor = forms.ModelChoiceField(
        queryset=Entidades.objects.none(), 
        label='Fornecedor',
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    numero = forms.IntegerField(
        label='Número',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    serie = forms.CharField(
        max_length=3, 
        label='Série',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    data_emissao = forms.DateField(
        label='Data Emissão',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    data_entrada = forms.DateField(
        label='Data Entrada',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    valor_total = forms.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        label='Valor Total',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    def __init__(self, *args, **kwargs):
        empresa_id = kwargs.pop('empresa_id', None)
        using_db = kwargs.pop('using_db', 'default')
        super().__init__(*args, **kwargs)
        
        if empresa_id:
            # Filter suppliers (Assuming FO=Fornecedor, AM=Ambos)
            self.fields['fornecedor'].queryset = Entidades.objects.using(using_db).filter(
                enti_empr=empresa_id,
                enti_tipo_enti__in=['FO', 'AM']
            ).order_by('enti_nome')
