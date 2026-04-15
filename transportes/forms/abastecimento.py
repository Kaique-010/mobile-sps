from django import forms
from transportes.models import Abastecusto


class AbastecimentoForm(forms.ModelForm):
    frota_display = forms.CharField(label="Frota/Transportadora", required=False)
    veiculo_display = forms.CharField(label="Veículo(sequencia)", required=False)
    funcionario_display = forms.CharField(label="Funcionário", required=False)
    fornecedor_display = forms.CharField(label="Fornecedor", required=False)
    bomba_display = forms.CharField(label="Bomba", required=False)
    combustivel_display = forms.CharField(label="Combustível", required=False)
    abas_frot = forms.CharField(widget=forms.HiddenInput())
    abas_veic_sequ = forms.IntegerField(required=False, widget=forms.HiddenInput())
    abas_func = forms.IntegerField(required=False, widget=forms.HiddenInput())
    abas_enti = forms.IntegerField(required=False, widget=forms.HiddenInput())
    abas_bomb = forms.CharField(required=False, widget=forms.HiddenInput())
    abas_comb = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Abastecusto
        fields = (
            "abas_data",
            "abas_frot",
            "abas_veic_sequ",
            "abas_func",
            "abas_enti",
            "abas_bomb",
            "abas_comb",
            "abas_quan",
            "abas_unit",
            "abas_tota",
            "abas_hokm",
            "abas_hokm_ante",
            "abas_obse",
        )

        widgets = {
            "abas_data": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "abas_quan": forms.NumberInput(attrs={"class": "form-control"}),
            "abas_unit": forms.NumberInput(attrs={"class": "form-control"}),
            "abas_tota": forms.NumberInput(attrs={"class": "form-control", "readonly": "readonly"}),
            "abas_hokm": forms.NumberInput(attrs={"class": "form-control"}),
            "abas_hokm_ante": forms.NumberInput(attrs={"class": "form-control"}),
            "abas_obse": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

        labels = {
            "abas_data": "Data do abastecimento",
            "abas_frot": "Frota/Transportadora",
            "abas_veic_sequ": "Veículo(sequencia)",
            "abas_func": "Funcionário",
            "abas_enti": "Fornecedor",
            "abas_bomb": "Bomba",
            "abas_comb": "Combustível",
            "abas_quan": "Quantidade",
            "abas_unit": "Preço Unitário",
            "abas_hokm": "Horímetro Atual",
            "abas_hokm_ante": "Horímetro Anterior",
            "abas_obse": "Observações",
            "abas_tota": "Total Abastecido em R$",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔥 aplica bootstrap automaticamente nos campos visíveis
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs["class"] = "form-control"

        if "abas_tota" in self.fields:
            self.fields["abas_tota"].required = False
            self.fields["abas_tota"].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        is_create = not getattr(self.instance, "pk", None)

        if is_create and not cleaned_data.get("abas_frot"):
            raise forms.ValidationError("Selecione uma frota válida")
        if is_create and not cleaned_data.get("abas_veic_sequ"):
            raise forms.ValidationError("Selecione um veículo válido")
        if is_create and not cleaned_data.get("abas_bomb"):
            raise forms.ValidationError("Selecione uma bomba válida")
        if is_create and not cleaned_data.get("abas_comb"):
            raise forms.ValidationError("Selecione um combustível válido")

        return cleaned_data
