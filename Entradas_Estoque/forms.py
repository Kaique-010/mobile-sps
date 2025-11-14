from django import forms
from django.forms.models import inlineformset_factory
from django.forms import formset_factory

from .models import EntradaEstoque
from Produtos.models import Produtos
from Licencas.models import Empresas


class EntradaEstoqueForm(forms.ModelForm):
    class Meta:
        model = EntradaEstoque
        fields = [
            'entr_prod', 'entr_enti', 'entr_data', 'entr_quan', 'entr_unit', 'entr_tota'
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
                'placeholder': 'Data da Entrada'
            }),
            'entr_quan': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Quantidade'
            }),
            'entr_unit': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Preço Unitário'
            }),
            'entr_tota': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Total',
                'readonly': True}),
            
        }
        
        def __init__(self) -> None:
            super().__init__()
            self.fields['entr_tota'].widget.attrs['readonly'] = True
        
        try:
            entidades_qs = Entidades.objects.using(database).all()[:40]
            if empresa_id:
                entidades_qs = entidades_qs.filter(enti_empr=str(empresa_id))
            
            self.fields['entr_enti'].queryset = entidades_qs.order_by('enti_nome')
            self.fields['entr_enti'].label_from_instance = lambda obj: f"{obj.enti_clie} - {obj.enti_nome}"
            self.fields['entr_enti'].empty_label = "Selecione uma entidade"
        except Exception as e:
            print(f"Erro ao carregar entidades: {e}")
            self.fields['entr_enti'].queryset = Entidades.objects.none()
        
        # Popula produtos (entr_prod)
        try:
            produtos_qs = Produtos.objects.using(database).filter(
                prod_codi__isnull=False,
                prod_empr__isnull=empresa_id is None
            )
            if empresa_id:
                produtos_qs = produtos_qs.filter(prod_empr=str(empresa_id))
            
            self.fields['entr_prod'].queryset = produtos_qs.order_by('prod_nome')
            self.fields['entr_prod'].label_from_instance = lambda obj: f"{obj.prod_codi} - {obj.prod_nome}"
            self.fields['entr_prod'].empty_label = "Selecione um produto"
        except Exception as e:
            print(f"Erro ao carregar produtos: {e}")
            self.fields['entr_prod'].queryset = Produtos.objects.none()

        def clean(self):
            cleaned = super().clean()
            logging.getLogger(__name__).debug(
                "[EntradaEstoqueForm.clean] entr_prod=%s entr_enti=%s entr_data=%s entr_quan=%s entr_unit=%s entr_tota=%s",
                cleaned.get('entr_prod'), cleaned.get('entr_enti'), cleaned.get('entr_data'), cleaned.get('entr_quan'), cleaned.get('entr_unit'), cleaned.get('entr_tota')
            )
            return cleaned
