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
    class Meta:
        model = EntradaEstoque
        fields = [
            'entr_prod', 'entr_enti', 'entr_data', 'entr_quan', 'entr_tota', 'entr_unit'
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
            
        }

    def __init__(self, *args, **kwargs):
        database = kwargs.pop('database', None)
        empresa_id = kwargs.pop('empresa_id', None)
        super().__init__(*args, **kwargs)
        self.fields['entr_tota'].widget.attrs['readonly'] = True
        try:
            from Entidades.models import Entidades
            from Produtos.models import Produtos
            if database:
                _ = Entidades.objects.using(database).all()[:1]
                _ = Produtos.objects.using(database).all()[:1]
        except Exception:
            pass

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
