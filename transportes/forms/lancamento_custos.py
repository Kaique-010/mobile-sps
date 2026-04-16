from django import forms

from transportes.models import Custos


class LancamentoCustosForm(forms.ModelForm):
    frota_display = forms.CharField(label="Frota/Transportadora", required=False)
    veiculo_display = forms.CharField(label="Veículo(sequencia)", required=False)
    funcionario_display = forms.CharField(label="Funcionário", required=False)
    fornecedor_display = forms.CharField(label="Fornecedor", required=False)
    produto_display = forms.CharField(label="Produto", required=False)

    lacu_frot = forms.CharField(widget=forms.HiddenInput())
    lacu_veic = forms.IntegerField(required=False, widget=forms.HiddenInput())
    lacu_moto = forms.IntegerField(required=False, widget=forms.HiddenInput())
    lacu_forn = forms.IntegerField(required=False, widget=forms.HiddenInput())
    lacu_item = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Custos
        fields = (
            "lacu_data",
            "lacu_frot",
            "lacu_veic",
            "lacu_moto",
            "lacu_forn",
            "lacu_item",
            "lacu_nome_item",
            "lacu_docu",
            "lacu_quan",
            "lacu_unit",
            "lacu_tota",
            "lacu_nota",
            "lacu_cupo",
            "lacu_obse",
        )
        widgets = {
            "lacu_data": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "lacu_nome_item": forms.TextInput(attrs={"class": "form-control", "placeholder": "Descrição do item", "readonly": "readonly"}),
            "lacu_docu": forms.TextInput(attrs={"class": "form-control", "placeholder": "Documento"}),
            "lacu_quan": forms.NumberInput(attrs={"class": "form-control", "step": "0.00001"}),
            "lacu_unit": forms.NumberInput(attrs={"class": "form-control", "step": "0.0001"}),
            "lacu_tota": forms.NumberInput(attrs={"class": "form-control", "readonly": "readonly"}),
            "lacu_nota": forms.NumberInput(attrs={"class": "form-control"}),
            "lacu_cupo": forms.NumberInput(attrs={"class": "form-control"}),
            "lacu_obse": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }
        labels = {
            "lacu_data": "Data do lançamento",
            "lacu_frot": "Frota/Transportadora",
            "lacu_veic": "Veículo (sequencial)",
            "lacu_moto": "Funcionário/Motorista",
            "lacu_forn": "Entidade/Fornecedor",
            "lacu_item": "Item/Insumo",
            "lacu_nome_item": "Descrição do item",
            "lacu_docu": "Documento",
            "lacu_quan": "Quantidade",
            "lacu_unit": "Preço unitário",
            "lacu_tota": "Total",
            "lacu_nota": "Nota fiscal",
            "lacu_cupo": "Cupom",
            "lacu_obse": "Observações",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for _field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs["class"] = "form-control"

        self.fields["lacu_tota"].required = False
        self.fields["lacu_tota"].disabled = True
        self.fields["lacu_nome_item"].required = False

    @staticmethod
    def _codigo_do_display(valor):
        raw = str(valor or "").strip()
        if not raw:
            return None
        if " - " in raw:
            raw = raw.split(" - ", 1)[0].strip()
        return raw or None

    def clean(self):
        cleaned_data = super().clean()
        is_create = not getattr(self.instance, "pk", None)

        if not cleaned_data.get("lacu_frot"):
            cod_frota = self._codigo_do_display(cleaned_data.get("frota_display"))
            if cod_frota:
                cleaned_data["lacu_frot"] = cod_frota
                

        if not cleaned_data.get("lacu_moto"):
            cod_func = self._codigo_do_display(cleaned_data.get("funcionario_display"))
            if cod_func and str(cod_func).isdigit():
                cleaned_data["lacu_moto"] = int(cod_func)

        if not cleaned_data.get("lacu_forn"):
            cod_forn = self._codigo_do_display(cleaned_data.get("fornecedor_display"))
            if cod_forn and str(cod_forn).isdigit():
                cleaned_data["lacu_forn"] = int(cod_forn)

        if not cleaned_data.get("lacu_item"):
            cod_item = self._codigo_do_display(cleaned_data.get("produto_display"))
            if cod_item:
                cleaned_data["lacu_item"] = cod_item

        if is_create and not cleaned_data.get("lacu_frot"):
            raise forms.ValidationError("Selecione uma frota/transportadora válida.")
        if cleaned_data.get('lacu_frot'):
            cleaned_data["lacu_tran"] = cleaned_data["lacu_frot"]
        else:
            cleaned_data["lacu_tran"] = None
        if is_create and not cleaned_data.get("lacu_veic"):
            raise forms.ValidationError("Selecione um veículo válido.")
        if is_create and not cleaned_data.get("lacu_moto") and not cleaned_data.get("lacu_forn"):
            raise forms.ValidationError("Selecione um funcionário ou uma entidade/fornecedor.")
        if is_create and not cleaned_data.get("lacu_item"):
            raise forms.ValidationError("Selecione um produto válido.")
        return cleaned_data
