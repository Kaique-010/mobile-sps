from django import forms
from django.forms import inlineformset_factory
from .models import PedidoVenda, Itenspedidovenda
from Produtos.models import Produtos
 
class PedidoVendaForm(forms.ModelForm):
    class Meta:
        model = PedidoVenda
        fields = [
            'pedi_forn',
            'pedi_data',
            'pedi_tota',
            'pedi_fina',
            'pedi_vend',
        ]
        widgets = {
            'pedi_forn': forms.Select(attrs={'class': 'form-control'}),
            'pedi_data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'pedi_tota': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0,0'}),
            'pedi_fina': forms.Select(attrs={'class': 'form-control', 'placeholder': 'FINANCEIRO'}),
            'pedi_vend': forms.Select(attrs={'class': 'form-control'}),
           
        }

class ItensPedidoVendaForm(forms.ModelForm):
    iped_prod = forms.ModelChoiceField(queryset=Produtos.objects.all(), label="Produto")

    class Meta:
        model = Itenspedidovenda
        fields = ['iped_prod', 'iped_quan', 'iped_unit']  
        widgets = {
            'iped_pedi': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Pedido'}),
            'iped_quan': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantidade'}),
            'iped_unit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Valor Unitário'}),
            'iped_tota': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Total'}),
            'iped_fret': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Frete'}),
            'iped_desc': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Desconto'}),
            'iped_unli': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Unidade'}),
            'iped_tipo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tipo'}),
            'iped_desc_item': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Descrição do Item'}),
            'iped_perc_desc': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Percentual Desconto'}),
            'iped_unme': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unidade de Medida'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        optional_fields = [
            'iped_pedi', 'iped_tota', 'iped_fret', 'iped_desc', 'iped_unli',
            'iped_tipo', 'iped_desc_item', 'iped_perc_desc', 'iped_unme'
        ]
        for fname in optional_fields:
            if fname in self.fields:
                self.fields[fname].required = False


    
    
    