from django import forms
from django.forms import inlineformset_factory
from .models import PedidoVenda, Itenspedidovenda
from Produtos.models import Produtos
 
 

ItemPedidoFormSet = inlineformset_factory(
    PedidoVenda,
    Itenspedidovenda,
    fields=('iped_unit', 'iped_quan', 'iped_prod', 'iped_empr', 'iped_fili'),  
    extra=1,  
    can_delete=True,  # Permite a exclusão de itens
    exclude=('iped_item',)  
)

class PedidoVendaForm(forms.ModelForm):
    class Meta:
        model = PedidoVenda
        fields = [
            'pedi_empr',
            'pedi_fili',
            'pedi_forn',
            'pedi_data',
            'pedi_tota',
            'pedi_fina',
            'pedi_vend',
        ]
        widgets = {
            'pedi_empr': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Insira a Empresa'}),
            'pedi_fili': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Insira a Filial'}),
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
            'iped_empr': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Empresa'}),
            'iped_fili': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Filial'}),
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
        
        self.fields['iped_empr'].required = False
        self.fields['iped_fili'].required = False  
        self.fields['iped_pedi'].required = False
        self.fields['iped_tota'].required = False
        self.fields['iped_fret'].required = False
        self.fields['iped_desc'].required = False
        self.fields['iped_unli'].required = False
        self.fields['iped_tipo'].required = False
        self.fields['iped_desc_item'].required = False
        self.fields['iped_perc_desc'].required = False
        self.fields['iped_unme'].required = False


    
    
    