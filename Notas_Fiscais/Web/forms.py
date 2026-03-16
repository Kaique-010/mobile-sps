# notas_fiscais/forms.py

from django import forms
from django.forms import inlineformset_factory
from ..models import Nota, NotaItem, NotaItemImposto, Transporte
from Entidades.models import Entidades
from Produtos.models import Produtos


NATUREZA_OPERACAO_CHOICES = [
    ("Venda de mercadoria", "Venda de mercadoria"),
    ("Venda de produção do estabelecimento", "Venda de produção do estabelecimento"),
    ("Devolução de venda", "Devolução de venda"),
    ("Remessa", "Remessa"),
]


class NotaForm(forms.ModelForm):
    natureza_operacao = forms.ChoiceField(
        choices=NATUREZA_OPERACAO_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
        initial="Venda de mercadoria",
        required=False,
    )
    destinatario = forms.ModelChoiceField(
        queryset=Entidades.objects.none(),
        widget=forms.Select(attrs={"class": "form-control select2"}),
        help_text="Cliente / Destinatário da nota"
    )

    class Meta:
        model = Nota
        fields = [
            "modelo", "serie", "numero",
            "data_emissao", "data_saida",
            "tipo_operacao", "finalidade", "ambiente",
            "destinatario",
        ]

        widgets = {
            "modelo": forms.Select(attrs={"class": "form-control"}),
            "data_emissao": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "data_saida": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "serie": forms.TextInput(attrs={"class": "form-control"}),
            "numero": forms.NumberInput(attrs={"class": "form-control"}),
            "tipo_operacao": forms.Select(attrs={"class": "form-control"}),
            "finalidade": forms.Select(attrs={"class": "form-control"}),
            "ambiente": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        database = kwargs.pop("database", "default")
        empresa_id = kwargs.pop("empresa_id", None)

        super().__init__(*args, **kwargs)

        if empresa_id:
            self.fields["destinatario"].queryset = Entidades.objects.using(database).filter(
                enti_empr=empresa_id,
                enti_tipo_enti__in=["CL", "AM"]
            )


class NotaItemForm(forms.ModelForm):
    produto = forms.ModelChoiceField(
        queryset=Produtos.objects.none(),
        required=False,
        widget=forms.HiddenInput(attrs={"class": "form-control"}),
    )
    class Meta:
        model = NotaItem
        fields = [
            "produto",
            "quantidade", "unitario", "desconto",   
            "cfop", "ncm", "cest",
            "cst_icms", "cst_pis", "cst_cofins",
            "cst_ibs", "cst_cbs",
        ]
        widgets = {
            "quantidade": forms.NumberInput(attrs={"step": "0.0001", "class": "form-control"}),
            "unitario": forms.NumberInput(attrs={"step": "0.0001", "class": "form-control"}),
            "desconto": forms.NumberInput(attrs={"step": "0.0001", "class": "form-control"}),
            "cfop": forms.TextInput(attrs={"class": "form-control"}),
            "ncm": forms.TextInput(attrs={"class": "form-control"}),
            "cest": forms.TextInput(attrs={"class": "form-control"}),
            "cst_icms": forms.TextInput(attrs={"class": "form-control"}),
            "cst_pis": forms.TextInput(attrs={"class": "form-control"}),
            "cst_cofins": forms.TextInput(attrs={"class": "form-control"}),
            "cst_ibs": forms.TextInput(attrs={"class": "form-control"}),
            "cst_cbs": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        database = kwargs.pop("database", "default")
        empresa_id = kwargs.pop("empresa_id", None)
        super().__init__(*args, **kwargs)

        for f in ["cfop", "ncm", "cst_icms", "cst_pis", "cst_cofins", "cst_ibs", "cst_cbs", "cest"]:
            if f in self.fields:
                self.fields[f].required = False

        qs = Produtos.objects.using(database)
        if empresa_id is not None:
            qs = qs.filter(prod_empr=str(empresa_id))
        self.fields["produto"].queryset = qs

        if self.instance and self.instance.pk:
            self.fields["produto"].initial = self.instance.produto_id


# Formset de itens
NotaItemFormSet = inlineformset_factory(
    Nota,
    NotaItem,
    form=NotaItemForm,
    extra=0,
    can_delete=True
)



class NotaItemImpostoForm(forms.ModelForm):
    class Meta:
        model = NotaItemImposto
        fields = [
            "icms_base", "icms_aliquota", "icms_valor",
            "ipi_valor", "pis_valor", "cofins_valor",
            "fcp_valor",
            "ibs_base", "ibs_aliquota", "ibs_valor",
            "cbs_base", "cbs_aliquota", "cbs_valor",
        ]
        widgets = {
            "icms_aliquota": forms.NumberInput(attrs={"step": "0.01"}),
            "ibs_aliquota": forms.NumberInput(attrs={"step": "0.01"}),
            "cbs_aliquota": forms.NumberInput(attrs={"step": "0.01"}),
        }




class TransporteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "transportadora" in self.fields:
            self.fields["transportadora"].required = False

    class Meta:
        model = Transporte
        fields = [
            "modalidade_frete",
            "transportadora",
            "placa_veiculo",
            "uf_veiculo",
        ]
        widgets = {
            "modalidade_frete": forms.Select(attrs={"class": "form-control"}),
            "transportadora": forms.TextInput(attrs={"class": "form-control"}),
            "placa_veiculo": forms.TextInput(attrs={"class": "form-control"}),
            "uf_veiculo": forms.TextInput(attrs={"class": "form-control"}),
        }


class EnviarXmlContabilidadeForm(forms.Form):
    data_inicio = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    data_fim = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    emails = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "email@dominio.com; outro@dominio.com"}),
        required=True,
    )
