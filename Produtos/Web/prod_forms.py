from django import forms
from django.forms.models import inlineformset_factory
from django.forms import formset_factory
from Produtos.models import Produtos, GrupoProduto, SubgrupoProduto, FamiliaProduto, Marca, Tabelaprecos, UnidadeMedida

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
            'prod_fami', 'prod_loca', 'prod_ncm', 'prod_marc', 'prod_gtin'
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
            'prod_gtin': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'GTIN'
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
        self.fields['prod_gtin'].required = False

class UnidadeMedidaForm(forms.ModelForm):
    class Meta:
        model = UnidadeMedida
        fields = ['unid_codi', 'unid_desc']
        widgets = {
            'unid_codi': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Código'
            }),
            'unid_desc': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Descrição'
            }),
            }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'unid_desc' in self.fields:
            self.fields['unid_desc'].required = False

class GrupoForm(forms.ModelForm):
   class Meta:
       model = GrupoProduto
       fields = '__all__'
       widgets = {
            'codigo': forms.HiddenInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Código'
            }),
            'descricao': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Descrição'
            }),
            }
   def __init__(self, *args, **kwargs):
       super().__init__(*args, **kwargs)
       if 'codigo' in self.fields:
           self.fields['codigo'].required = False
       

class SubgrupoForm(forms.ModelForm):
   class Meta:
       model = SubgrupoProduto
       fields = '__all__'
       widgets = {
            'codigo': forms.HiddenInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Código'
            }),
            'descricao': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Descrição'
            }),
            }
   def __init__(self, *args, **kwargs):
       super().__init__(*args, **kwargs)
       if 'codigo' in self.fields:
           self.fields['codigo'].required = False


class FamiliaForm(forms.ModelForm):
    class Meta:
        model= FamiliaProduto
        fields = '__all__'
        widgets = {
            'codigo': forms.HiddenInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Código'
            }),
            'descricao': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Descrição'
            }),
            }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'codigo' in self.fields:
            self.fields['codigo'].required = False
        
class MarcaForm(forms.ModelForm):
   class Meta:
       model = Marca
       fields = '__all__'
       widgets = {
            'codigo': forms.HiddenInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Código'
            }),
            'nome': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nome'
            }),
            }
   def __init__(self, *args, **kwargs):
       super().__init__(*args, **kwargs)
       if 'codigo' in self.fields:
           self.fields['codigo'].required = False
    


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

        def norm(v):
            if v is None:
                return Decimal('0')
            if isinstance(v, Decimal):
                return v
            try:
                if isinstance(v, (int, float)):
                    return Decimal(str(v))
                s = str(v).strip().replace('.', '').replace(',', '.') if isinstance(v, str) else str(v)
                return Decimal(s or '0')
            except Exception:
                return Decimal('0')

        prco = norm(cleaned.get('tabe_prco'))
        perc_frete = norm(cleaned.get('tabe_fret'))
        despesas = norm(cleaned.get('tabe_desp'))
        marg = norm(cleaned.get('tabe_marg'))
        perc_prazo = norm(cleaned.get('tabe_praz'))

        valor_frete = prco * (perc_frete / Decimal('100'))
        custo_gerencial = prco + valor_frete + despesas
        custo_gerencial_q = custo_gerencial.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        preco_vista = prco * (Decimal('1') + (marg / Decimal('100')))
        preco_vista_q = preco_vista.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        preco_prazo = preco_vista * (Decimal('1') + (perc_prazo / Decimal('100')))
        preco_prazo_q = preco_prazo.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        cleaned['tabe_cuge'] = custo_gerencial_q
        cleaned['tabe_cust'] = custo_gerencial_q
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
)

TabelaprecosFormSetUpdate = forms.modelformset_factory(
    Tabelaprecos,
    form=TabelaprecosForm,
    extra=0,
)
