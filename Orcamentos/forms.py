from django import forms
from Entidades.models import Entidades
from Produtos.models import Produtos
from .models import Orcamentos, ItensOrcamento, STATUS_ORCAMENTO
from django.forms import inlineformset_factory
from django.db.models import Max


class OrcamentoForm(forms.ModelForm):
    class Meta:
        model = Orcamentos
        fields = [
            'pedi_empr', 'pedi_fili', 'pedi_nume', 'pedi_data', 'pedi_forn',
            'pedi_vend', 'pedi_obse',
            'pedi_desc', 'pedi_tota'
        ]
        widgets = {
            'pedi_empr': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Empresa'}),
            'pedi_fili': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Filial'}),
            'pedi_nume': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Código do orçamento'}),
            'pedi_data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'pedi_forn': forms.HiddenInput(),
            'pedi_vend': forms.HiddenInput(),
            'pedi_obse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'pedi_desc': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'pedi_tota': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pedi_forn'].queryset = Entidades.objects.filter(enti_tipo_enti__in=['CL', 'AM'])  # Clientes e Ambos
        self.fields['pedi_vend'].queryset = Entidades.objects.filter(enti_tipo_enti__in=['VE', 'AM'])  # Vendedores e Ambos

    def save(self, commit=True):
        orcamento = super().save(commit=False)

        if orcamento.pedi_nume is None or orcamento.pedi_nume == 0:
            max_nume = Orcamento.objects.aggregate(max_nume=Max('pedi_nume'))['max_nume'] or 0
            orcamento.pedi_nume = max_nume + 1

        if commit:
            orcamento.save()

        return orcamento


class OrcamentoPecasForm(forms.ModelForm):
    class Meta:
        model = ItensOrcamento  # Corrigido, sem parênteses
        fields = ['iped_pedi', 'iped_prod', 'iped_quan', 'iped_unit', 'iped_tota']
        widgets = {
            'iped_pedi': forms.Select(attrs={'class': 'form-control'}),
            'iped_prod': forms.Select(attrs={'class': 'form-control'}),
            'iped_quan': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'iped_unit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'iped_tota': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
        }

    def clean_iped_quan(self):
        quantidade = self.cleaned_data.get('iped_quan')
        if quantidade is not None and quantidade <= 0:
            raise forms.ValidationError("A quantidade deve ser maior que zero.")
        return quantidade

    def clean_iped_unit(self):
        preco_unitario = self.cleaned_data.get('iped_unit')
        if preco_unitario is not None and preco_unitario <= 0:
            raise forms.ValidationError("O preço unitário deve ser maior que zero.")
        return preco_unitario


def get_orcamento_pecas_inline_formset():
    """Cria o inline formset sob demanda para ambientes onde há FK configurada.
    Evita erro de import quando não existe FK explícita entre os modelos.
    """
    return inlineformset_factory(
        Orcamentos,
        ItensOrcamento,
        form=OrcamentoPecasForm,
        extra=1,
        can_delete=True
    )


# ====== Formulários Web (espelhando Pedidos) ======

class OrcamentoVendaForm(forms.ModelForm):
    class Meta:
        model = Orcamentos
        fields = [
            'pedi_data', 'pedi_forn', 'pedi_vend', 'pedi_stat', 'pedi_topr', 'pedi_desc', 'pedi_tota'
        ]
        widgets = {
            'pedi_data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'pedi_forn': forms.HiddenInput(),
            'pedi_vend': forms.HiddenInput(),
            'pedi_stat': forms.Select(attrs={'class': 'form-select'}),
            'pedi_topr': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
            'pedi_desc': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'pedi_tota': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        self.database = kwargs.pop('database', None)
        self.empresa_id = kwargs.pop('empresa_id', None)
        super().__init__(*args, **kwargs)
        self.fields['pedi_stat'].choices = STATUS_ORCAMENTO
        self.fields['pedi_stat'].initial = '0'

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('pedi_forn'):
            self.add_error('pedi_forn', 'Cliente é obrigatório')
        return cleaned


class ItensOrcamentoVendaForm(forms.ModelForm):
    class Meta:
        model = ItensOrcamento
        fields = ['iped_prod', 'iped_quan', 'iped_unit']
        widgets = {
            'iped_prod': forms.HiddenInput(),
            'iped_quan': forms.NumberInput(attrs={'class': 'form-control text-end', 'min': '1', 'value': '1'}),
            'iped_unit': forms.NumberInput(attrs={'class': 'form-control text-end', 'step': '0.01', 'value': '0.00'}),
        }

    def __init__(self, *args, **kwargs):
        self.database = kwargs.pop('database', None)
        self.empresa_id = kwargs.pop('empresa_id', None)
        super().__init__(*args, **kwargs)
