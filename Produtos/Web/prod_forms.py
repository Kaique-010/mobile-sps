from django import forms
from django.forms.models import inlineformset_factory
from django.forms import formset_factory
from Produtos.models import Produtos, GrupoProduto, SubgrupoProduto, FamiliaProduto, Marca, Tabelaprecos

class ProdutosForm(forms.ModelForm):
    # Campo de upload de foto desacoplado do BinaryField do modelo
    prod_foto = forms.FileField(required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control-file'}))
    # Campo livre para Código do Fabricante (não pertence ao modelo)
    prod_codi_fabr_field = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Código do Fabricante'
    }))
    class Meta:
        model = Produtos
        fields = [
            'prod_codi', 'prod_nome', 'prod_unme', 'prod_grup', 'prod_sugr',
            'prod_fami', 'prod_loca', 'prod_ncm', 'prod_marc'
        ]
        widgets = {
            'prod_codi': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Deixe em branco para código sequencial'
            }),
            'prod_nome': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nome do Produto'
            }),
            'prod_unme': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Unidade de Medida'
            }),
            'prod_grup': forms.Select(attrs={
                'class': 'form-control', 
                'placeholder': 'Grupo'
            }),
            'prod_sugr': forms.Select(attrs={
                'class': 'form-control', 
                'placeholder': 'Subgrupo'
            }),
            'prod_fami': forms.Select(attrs={
                'class': 'form-control', 
                'placeholder': 'Família'
            }),
            'prod_loca': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Local'
            }),
            'prod_ncm': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'NCM'
            }),
            'prod_marc': forms.Select(attrs={
                'class': 'form-control', 
                'placeholder': 'Marca'
            }),
          
        }
    
    def __init__(self, *args, **kwargs):
        super(ProdutosForm, self).__init__(*args, **kwargs)
        # Configurando campos opcionais
        self.fields['prod_grup'].required = False
        self.fields['prod_sugr'].required = False  
        self.fields['prod_fami'].required = False
        self.fields['prod_loca'].required = False
        self.fields['prod_marc'].required = False  
        self.fields['prod_foto'].required = False
        self.fields['prod_codi'].required = False

class GrupoForm(forms.ModelForm):
   class Meta:
       model = GrupoProduto
       fields = '__all__'
       widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Código'
            }),
            'descricao': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Descrição'
            }),
            }
       

class SubgrupoForm(forms.ModelForm):
   class Meta:
       model = SubgrupoProduto
       fields = '__all__'
       widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Código'
            }),
            'descricao': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Descrição'
            }),
            }


class FamiliaForm(forms.ModelForm):
    class Meta:
        model= FamiliaProduto
        fields = '__all__'
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Código'
            }),
            'descricao': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Descrição'
            }),
            }
        
class MarcaForm(forms.ModelForm):
   class Meta:
       model = Marca
       fields = '__all__'
       widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Código'
            }),
            'nome': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nome'
            }),
            }
    


class TabelaprecosForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'tabe_fili' in self.fields:
            self.fields['tabe_fili'].required = False

    class Meta:
        model = Tabelaprecos
        fields = [
            'tabe_fili', 'tabe_prco', 'tabe_icms', 'tabe_desc', 'tabe_vipi', 'tabe_pipi', 'tabe_fret', 
            'tabe_desp', 'tabe_cust', 'tabe_marg', 'tabe_impo', 'tabe_avis', 'tabe_praz', 'tabe_apra', 
            'tabe_vare', 'field_log_data', 'field_log_time', 'tabe_valo_st', 'tabe_perc_reaj', 'tabe_hist',
            'tabe_cuge', 'tabe_entr', 'tabe_perc_st'
        ]

        widgets = {
            'tabe_prco': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Preço de Compra'}),
            'tabe_fret': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'decimal', 'placeholder': '% Frete'}),
            'tabe_desp': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'decimal', 'placeholder': 'Despesas'}),
            'tabe_marg': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'decimal', 'placeholder': '% a vista'}),
            'tabe_avis': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'readonly': 'readonly'
            }),
            'tabe_praz': forms.TextInput(attrs={
                'class': 'form-control',
                'inputmode': 'decimal',
                'placeholder': '% a prazo'
            }),
            'tabe_apra': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'readonly': 'readonly'
            }),
            'tabe_hist': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Histórico'}),
            'tabe_cuge': forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
        }),
            
        }

    def clean(self):
        cleaned = super().clean()
        from decimal import Decimal, ROUND_HALF_UP
        D = lambda v: (v if isinstance(v, Decimal) else Decimal(str(v or 0)))

        prco = D(cleaned.get('tabe_prco'))
        perc_frete = D(cleaned.get('tabe_fret'))
        cuge = D(cleaned.get('tabe_cuge'))
        marg = D(cleaned.get('tabe_marg'))
        perc_prazo = D(cleaned.get('tabe_praz'))

        valor_frete = prco * (perc_frete / D(100))
        custo_gerencial = prco + valor_frete + cuge
        custo_gerencial_q = custo_gerencial.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        preco_vista = prco * (D(1) + (marg / D(100)))
        preco_vista_q = preco_vista.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        preco_prazo = preco_vista * (D(1) + (perc_prazo / D(100)))
        preco_prazo_q = preco_prazo.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        cleaned['tabe_cuge'] = custo_gerencial_q
        cleaned['tabe_avis'] = preco_vista_q
        cleaned['tabe_apra'] = preco_prazo_q
        return cleaned

TabelaprecosFormSet = forms.modelformset_factory(
    Tabelaprecos,
    form=TabelaprecosForm,
    extra=1,
)

# Formset simples (sem PK/id oculto), usado para POST seguro
TabelaprecosPlainFormSet = formset_factory(
    TabelaprecosForm,
    extra=0,
    can_delete=True,
    formset=TabelaprecosFormSet,
)

TabelaprecosFormSetUpdate = forms.modelformset_factory(
    Tabelaprecos,
    form=TabelaprecosForm,
    extra=0,
)