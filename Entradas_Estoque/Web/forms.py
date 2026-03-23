from django import forms
from django.forms.models import inlineformset_factory
from django.forms import formset_factory
from Entidades.models import Entidades
from ..models import EntradaEstoque
from Produtos.models import Produtos
from Licencas.models import Empresas
import logging
logger = logging.getLogger(__name__)


class EntradaEstoqueForm(forms.ModelForm):
    auto_lote = forms.BooleanField(
        required=False,
        initial=False,
        label='Gerar lote sequencial'
    )
    lote_data_fabr = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Data Fabricação'
    )
    lote_data_vali = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Data Validade'
    )
    atualizar_preco = forms.BooleanField(
        required=False,
        initial=True,
        label='Atualizar tabela de preços'
    )
    preco_vista = forms.DecimalField(
        required=False,
        decimal_places=2,
        max_digits=15,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'inputmode': 'decimal', 'placeholder': 'Preço à vista'}),
        label='Preço à vista'
    )
    preco_prazo = forms.DecimalField(
        required=False,
        decimal_places=2,
        max_digits=15,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'inputmode': 'decimal', 'placeholder': 'Preço a prazo'}),
        label='Preço a prazo'
    )
    class Meta:
        model = EntradaEstoque
        fields = [
            'entr_prod', 'entr_enti', 'entr_data', 'entr_quan', 'entr_tota', 'entr_unit', 'entr_lote_vend'
        ]
        widgets = {
            'entr_prod': forms.HiddenInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Produto'
            }),
            'entr_enti': forms.HiddenInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Entidade Responsável'
            }),
            'entr_data': forms.DateInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Data da Entrada',
                'type': 'date'
            }),
            'entr_quan': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Quantidade',
                'step': '0.01',
                'inputmode': 'decimal'
            }),
            'entr_unit': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Preço Unitário',
                'step': '0.01',
                'inputmode': 'decimal'
            }),
            'entr_tota': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Total',
                'readonly': True}),
            'entr_lote_vend': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lote',
            }),
            
        }

    def __init__(self, *args, **kwargs):
        database = kwargs.pop('database', None)
        empresa_id = kwargs.pop('empresa_id', None)
        super().__init__(*args, **kwargs)
        self.fields['entr_tota'].widget.attrs['readonly'] = True
        
        if database:
            try:
                from Entidades.models import Entidades
                from Produtos.models import Produtos
                
                qs_entidades = Entidades.objects.using(database).all()
                qs_produtos = Produtos.objects.using(database).all()
                
                if empresa_id:
                    qs_entidades = qs_entidades.filter(enti_empr=empresa_id)
                    qs_produtos = qs_produtos.filter(prod_empr=empresa_id)
                
                self.fields['entr_enti'].queryset = qs_entidades
                self.fields['entr_prod'].queryset = qs_produtos
            except Exception as e:
                logger.error(f"Erro ao configurar querysets no form: {e}")

    def clean(self):
        cleaned = super().clean()
        logging.getLogger(__name__).debug(
            "[EntradaEstoqueForm.clean] entr_prod=%s entr_enti=%s entr_data=%s entr_quan=%s entr_unit=%s entr_tota=%s",
            cleaned.get('entr_prod'), cleaned.get('entr_enti'), cleaned.get('entr_data'), cleaned.get('entr_quan'), cleaned.get('entr_unit'), cleaned.get('entr_tota')
        )
        try:
            from decimal import Decimal, ROUND_HALF_UP
            q = cleaned.get('entr_quan') or Decimal('0')
            u_raw = cleaned.get('entr_unit')
            u = Decimal(str(u_raw or '0'))
            total = (q * u).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            cleaned['entr_tota'] = total
        except Exception:
            pass
        return cleaned

    def clean_entr_lote_vend(self):
        value = self.cleaned_data.get('entr_lote_vend')
        if value is None or value == '':
            return None
        if isinstance(value, int):
            return value
        try:
            s = str(value).strip()
        except Exception:
            return None
        if not s:
            return None
        if s.isdigit():
            return int(s)
        try:
            import re
            parts = re.findall(r'(\d+)', s)
            if parts:
                return int(parts[-1])
        except Exception:
            pass
        return None
