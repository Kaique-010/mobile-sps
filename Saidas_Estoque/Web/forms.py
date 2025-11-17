from django import forms
from Saidas_Estoque.models import SaidasEstoque
from decimal import Decimal


class SaidasEstoqueForm(forms.ModelForm):
    valor_unitario = forms.DecimalField(required=False, min_value=0, widget=forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': 'Preço Unitário',
        'step': '0.01',
        'inputmode': 'decimal'
    }))

    class Meta:
        model = SaidasEstoque
        fields = ['said_prod', 'said_enti', 'said_data', 'said_quan', 'said_tota']
        widgets = {
            'said_prod': forms.HiddenInput(attrs={'class': 'form-control', 'placeholder': 'Produto'}),
            'said_enti': forms.HiddenInput(attrs={'class': 'form-control', 'placeholder': 'Entidade Responsável'}),
            'said_data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'placeholder': 'Data da Saída'}),
            'said_quan': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantidade', 'step': '0.01', 'inputmode': 'decimal'}),
            'said_tota': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Total', 'readonly': True}),
        }

    def clean(self):
        cleaned = super().clean()
        quan = cleaned.get('said_quan')
        unit = cleaned.get('valor_unitario')
        if quan is not None and unit is not None:
            total = (quan * unit)
            try:
                total = total.quantize(Decimal('0.01'))
            except Exception:
                pass
            cleaned['said_tota'] = total
        return cleaned

    def __init__(self, *args, **kwargs):
        database = kwargs.pop('database', None)
        empresa_id = kwargs.pop('empresa_id', None)
        super().__init__(*args, **kwargs)
        self.fields['said_tota'].widget.attrs['readonly'] = True

    def clean(self):
        cleaned = super().clean()
        try:
            from decimal import Decimal, ROUND_HALF_UP
            q = cleaned.get('said_quan') or Decimal('0')
            u = cleaned.get('valor_unitario') or Decimal('0')
            total = (q * u).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            cleaned['said_tota'] = total
        except Exception:
            pass
        return cleaned