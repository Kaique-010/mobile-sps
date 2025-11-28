# notas_fiscais/forms.py

from django import forms
from django.forms import inlineformset_factory
from ..models import Nota, NotaItem, NotaItemImposto, Transporte
from Entidades.models import Entidades


class NotaForm(forms.ModelForm):
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
    class Meta:
        model = NotaItem
        fields = [
            "produto",
            "quantidade", "unitario", "desconto",
            "cfop", "ncm", "cest",
            "cst_icms", "cst_pis", "cst_cofins",
            "total",
        ]
        widgets = {
            "produto": forms.TextInput(attrs={"class": "form-control item-prod-ac"}),
            "quantidade": forms.NumberInput(attrs={"step": "0.0001", "class": "form-control"}),
            "unitario": forms.NumberInput(attrs={"step": "0.0001", "class": "form-control"}),
            "desconto": forms.NumberInput(attrs={"step": "0.0001", "class": "form-control"}),
            "cfop": forms.TextInput(attrs={"class": "form-control"}),
            "ncm": forms.TextInput(attrs={"class": "form-control"}),
            "cest": forms.TextInput(attrs={"class": "form-control"}),
            "cst_icms": forms.TextInput(attrs={"class": "form-control"}),
            "cst_pis": forms.TextInput(attrs={"class": "form-control"}),
            "cst_cofins": forms.TextInput(attrs={"class": "form-control"}),
        }


# Formset de itens
NotaItemFormSet = inlineformset_factory(
    Nota,
    NotaItem,
    form=NotaItemForm,
    extra=1,
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
