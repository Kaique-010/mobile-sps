from django import forms

from transportes.models import BombasSaldos


class BombasSaldosForm(forms.ModelForm):
    bomba_display = forms.CharField(label="Bomba", required=False)
    combustivel_display = forms.CharField(label="Combustível", required=False)
    bomb_bomb = forms.CharField(widget=forms.HiddenInput())
    bomb_comb = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = BombasSaldos
        fields = ("bomb_data", "bomb_bomb", "bomb_comb", "bomb_tipo_movi", "bomb_sald")

        widgets = {
            "bomb_data": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "bomb_tipo_movi": forms.Select(attrs={"class": "form-control"}),
            "bomb_sald": forms.NumberInput(attrs={"class": "form-control"}),
        }

        labels = {
            "bomb_data": "Data",
            "bomb_tipo_movi": "Tipo (Entrada/Saída)",
            "bomb_sald": "Quantidade",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("bomb_bomb"):
            raise forms.ValidationError("Selecione uma bomba válida")
        if not cleaned_data.get("bomb_comb"):
            raise forms.ValidationError("Selecione um combustível válido")
        return cleaned_data

