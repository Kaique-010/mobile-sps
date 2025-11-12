from django import forms
import logging
from django.forms import inlineformset_factory
from .models import PedidoVenda, Itenspedidovenda
from Produtos.models import Produtos
from Entidades.models import Entidades

class PedidoVendaForm(forms.ModelForm):
    class Meta:
        model = PedidoVenda
        fields = [
            'pedi_forn',
            'pedi_data',
            'pedi_topr',
            'pedi_tota',
            'pedi_fina',
            'pedi_vend',
            'pedi_desc',
        ]
        widgets = {
            'pedi_forn': forms.HiddenInput(),
            'pedi_data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'pedi_tota': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'readonly': True}),
            'pedi_topr': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'readonly': True}),
            'pedi_fina': forms.Select(attrs={'class': 'form-select'}),
            'pedi_vend': forms.HiddenInput(),
            'pedi_desc': forms.NumberInput(attrs={'class': 'form-control','placeholder': '0.00', 'step': '0.01'}),
        }
        labels = {
            'pedi_forn': 'Cliente',
            'pedi_data': 'Data',
            'pedi_topr': 'Subtotal',
            'pedi_tota': 'Total',
            'pedi_fina': 'Tipo Financeiro',
            'pedi_vend': 'Vendedor',
            'pedi_desc': 'Desconto',
        }

    def __init__(self, *args, **kwargs):
        # Recebe o banco de dados e empresa_id da view
        database = kwargs.pop('database', 'default')
        empresa_id = kwargs.pop('empresa_id', None)
        
        super().__init__(*args, **kwargs)
        
        # Popula clientes (pedi_forn)
        try:
            clientes_qs = Entidades.objects.using(database).filter(
                enti_tipo_enti__icontains='CL'  # Filtra apenas clientes
            )
            if empresa_id:
                clientes_qs = clientes_qs.filter(enti_empr=str(empresa_id))
            
            self.fields['pedi_forn'].queryset = clientes_qs.order_by('enti_nome')
            self.fields['pedi_forn'].label_from_instance = lambda obj: f"{obj.enti_clie} - {obj.enti_nome}"
            self.fields['pedi_forn'].empty_label = "Selecione um cliente"
        except Exception as e:
            print(f"Erro ao carregar clientes: {e}")
            self.fields['pedi_forn'].queryset = Entidades.objects.none()
        
        # Popula vendedores (pedi_vend)
        try:
            vendedores_qs = Entidades.objects.using(database).filter(
                enti_tipo_enti__icontains='VE'  # Filtra apenas vendedores
            )
            if empresa_id:
                vendedores_qs = vendedores_qs.filter(enti_empr=str(empresa_id))
            
            self.fields['pedi_vend'].queryset = vendedores_qs.order_by('enti_nome')
            self.fields['pedi_vend'].label_from_instance = lambda obj: f"{obj.enti_clie} - {obj.enti_nome}"
            self.fields['pedi_vend'].empty_label = "Selecione um vendedor"
        except Exception as e:
            print(f"Erro ao carregar vendedores: {e}")
            self.fields['pedi_vend'].queryset = Entidades.objects.none()
        
        # Opções de tipo financeiro (ajuste conforme seu modelo)
        self.fields['pedi_fina'].choices = [
            ('', 'Selecione o tipo'),
            ('0', 'À Vista'),
            ('1', 'A Prazo'),
            ('2', 'Sem Financeiro'),
            ('3', 'Na Emissão'),
        ]

    def clean(self):
        cleaned = super().clean()
        logging.getLogger(__name__).debug(
            "[PedidoVendaForm.clean] pedi_desc=%s pedi_topr=%s pedi_tota=%s pedi_fina=%s",
            cleaned.get('pedi_desc'), cleaned.get('pedi_topr'), cleaned.get('pedi_tota'), cleaned.get('pedi_fina')
        )
        return cleaned


class ItensPedidoVendaForm(forms.ModelForm):
    class Meta:
        model = Itenspedidovenda
        fields = ['iped_prod', 'iped_quan', 'iped_unit', 'iped_desc']
        widgets = {
            'iped_prod': forms.HiddenInput(),
            'iped_quan': forms.NumberInput(attrs={'class': 'form-control text-end', 'min': '1', 'value': '1'}),
            'iped_unit': forms.NumberInput(attrs={'class': 'form-control text-end', 'step': '0.01', 'value': '0.00'}),
            'iped_desc': forms.NumberInput(attrs={'class': 'form-control text-end', 'step': '0.01', 'value': '0.00'}),
        }
        labels = {
            'iped_prod': 'Produto',
            'iped_quan': 'Quantidade',
            'iped_unit': 'Preço Unitário',
            'iped_desc': 'Desconto',
        }

    def __init__(self, *args, **kwargs):
        database = kwargs.pop('database', 'default')
        empresa_id = kwargs.pop('empresa_id', None)
        
        super().__init__(*args, **kwargs)
        
        # Popula produtos
        try:
            produtos_qs = Produtos.objects.using(database).all()    
            if empresa_id:
                produtos_qs = produtos_qs.filter(prod_empr=str(empresa_id))
            
            self.fields['iped_prod'].queryset = produtos_qs.order_by('prod_nome')[:500]
            self.fields['iped_prod'].label_from_instance = lambda obj: f"{obj.prod_codi} - {obj.prod_nome}"
            self.fields['iped_prod'].empty_label = "Escolha um produto"
        except Exception as e:
            print(f"Erro ao carregar produtos: {e}")
            self.fields['iped_prod'].queryset = Produtos.objects.none()
        
        # Campos opcionais
        self.fields['iped_desc'].required = False

    def clean(self):
        cleaned = super().clean()
        logging.getLogger(__name__).debug(
            "[ItensPedidoVendaForm.clean] iped_prod=%s iped_quan=%s iped_unit=%s iped_desc=%s",
            cleaned.get('iped_prod'), cleaned.get('iped_quan'), cleaned.get('iped_unit'), cleaned.get('iped_desc')
        )
        return cleaned


