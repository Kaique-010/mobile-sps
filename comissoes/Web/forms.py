from django import forms
from comissoes.models import LancamentoComissao, PagamentoComissao, RegraComissao


def _parse_beneficiario(valor):
    v = str(valor or "").strip()
    if not v:
        return None
    head = v.split("-", 1)[0].strip()
    if head.isdigit():
        return int(head)
    if v.isdigit():
        return int(v)
    return None


class RegraComissaoForm(forms.ModelForm):
    beneficiario_busca = forms.CharField(required=True)

    class Meta:
        model = RegraComissao
        fields = [
            "regc_bene",
            "regc_perc",
            "regc_ativ",
            "regc_data_ini",
            "regc_data_fim",
        ]
        widgets = {
            "regc_data_ini": forms.DateInput(attrs={"type": "date"}),
            "regc_data_fim": forms.DateInput(attrs={"type": "date"}),
            "regc_perc": forms.NumberInput(attrs={"step": "0.01"}),
        }
        labels = {
            "regc_bene": RegraComissao._meta.get_field("regc_bene").verbose_name,
            "regc_perc": RegraComissao._meta.get_field("regc_perc").verbose_name,
            "regc_ativ": RegraComissao._meta.get_field("regc_ativ").verbose_name,
            "regc_data_ini": RegraComissao._meta.get_field("regc_data_ini").verbose_name,
            "regc_data_fim": RegraComissao._meta.get_field("regc_data_fim").verbose_name,
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        self.fields["beneficiario_busca"].label = self.fields["regc_bene"].label
        self.fields["beneficiario_busca"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Digite código ou nome...",
                "autocomplete": "off",
                "id": "beneficiario_busca",
                "list": "beneficiarios_options",
            }
        )

        self.fields["regc_bene"].widget = forms.HiddenInput()
        self.fields["regc_bene"].required = False
        self.fields["regc_perc"].widget.attrs.update({"class": "form-control", "placeholder": "Percentual"})
        self.fields["regc_ativ"].widget.attrs.update({"class": "form-check-input"})
        self.fields["regc_data_ini"].widget.attrs.update({"class": "form-control", "type": "date"})
        self.fields["regc_data_fim"].widget.attrs.update({"class": "form-control", "type": "date"})

        if self.instance and getattr(self.instance, "regc_bene", None):
            self.fields["beneficiario_busca"].initial = str(self.instance.regc_bene)

    def clean(self):
        cleaned = super().clean()
        bene = _parse_beneficiario(cleaned.get("beneficiario_busca"))
        if bene is None:
            bene = cleaned.get("regc_bene")
        if bene is None:
            raise forms.ValidationError("Informe o beneficiário.")
        cleaned["regc_bene"] = int(bene)
        return cleaned


class LancamentoFiltroForm(forms.Form):
    beneficiario_busca = forms.CharField(required=False, label=LancamentoComissao._meta.get_field("lcom_bene").verbose_name)
    tipo_origem = forms.ChoiceField(
        required=False,
        choices=[("", "Todos")] + list(LancamentoComissao.TIPO_ORIGEM_CHOICES),
        label=LancamentoComissao._meta.get_field("lcom_tipo_origem").verbose_name,
    )
    status = forms.ChoiceField(
        required=False,
        choices=[("", "Todos")] + [(str(x[0]), x[1]) for x in LancamentoComissao.STATUS_CHOICES],
        label="Status",
    )
    documento = forms.CharField(required=False, label=LancamentoComissao._meta.get_field("lcom_docu").verbose_name)
    data_ini = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="Data Inicial")
    data_fim = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="Data Final")
    valor_min = forms.DecimalField(required=False, decimal_places=2, max_digits=14, label="Valor (min)")
    valor_max = forms.DecimalField(required=False, decimal_places=2, max_digits=14, label="Valor (max)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "form-check-input"})
            elif isinstance(field.widget, (forms.Select,)):
                field.widget.attrs.update({"class": "form-select"})
            else:
                field.widget.attrs.update({"class": "form-control"})
        self.fields["beneficiario_busca"].widget.attrs.update(
            {"id": "beneficiario_busca", "list": "beneficiarios_options", "autocomplete": "off"}
        )

    def beneficiario_id(self):
        return _parse_beneficiario(self.cleaned_data.get("beneficiario_busca"))


class PagamentoFiltroForm(forms.Form):
    beneficiario_busca = forms.CharField(required=False, label=PagamentoComissao._meta.get_field("pagc_bene").verbose_name)
    data_ini = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="Data Inicial")
    data_fim = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="Data Final")
    valor_min = forms.DecimalField(required=False, decimal_places=2, max_digits=14, label="Valor (min)")
    valor_max = forms.DecimalField(required=False, decimal_places=2, max_digits=14, label="Valor (max)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})
        self.fields["beneficiario_busca"].widget.attrs.update(
            {"id": "beneficiario_busca", "list": "beneficiarios_options", "autocomplete": "off"}
        )

    def beneficiario_id(self):
        return _parse_beneficiario(self.cleaned_data.get("beneficiario_busca"))


class PagamentoCriarForm(forms.Form):
    beneficiario_busca = forms.CharField(required=True, label=PagamentoComissao._meta.get_field("pagc_bene").verbose_name)
    data = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={"type": "date"}),
        label=PagamentoComissao._meta.get_field("pagc_data").verbose_name,
    )
    observacao = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label=PagamentoComissao._meta.get_field("pagc_obse").verbose_name,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": "form-control"})
            else:
                field.widget.attrs.update({"class": "form-control"})
        self.fields["beneficiario_busca"].widget.attrs.update(
            {"id": "beneficiario_busca", "list": "beneficiarios_options", "autocomplete": "off"}
        )

    def beneficiario_id(self):
        bene = _parse_beneficiario(self.cleaned_data.get("beneficiario_busca"))
        if bene is None:
            raise forms.ValidationError("Informe o beneficiário.")
        return bene
