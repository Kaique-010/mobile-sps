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

    def __init__(self, *args, **kwargs):
        database = kwargs.pop('database', None)
        empresa_id = kwargs.pop('empresa_id', None)
        super().__init__(*args, **kwargs)
        self.fields['said_tota'].widget.attrs['readonly'] = True
        
        if database:
            try:
                from Entidades.models import Entidades
                from Produtos.models import Produtos
                
                qs_entidades = Entidades.objects.using(database).all()
                qs_produtos = Produtos.objects.using(database).all()
                
                if empresa_id:
                    qs_entidades = qs_entidades.filter(enti_empr=empresa_id)
                    qs_produtos = qs_produtos.filter(prod_empr=empresa_id)
                
                self.fields['said_enti'].queryset = qs_entidades
                self.fields['said_prod'].queryset = qs_produtos
            except Exception:
                pass

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