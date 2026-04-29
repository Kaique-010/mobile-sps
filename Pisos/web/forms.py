from django import forms
from Pisos.models import Pedidospisos


class PedidoPisosForm(forms.ModelForm):
    class Meta:
        model = Pedidospisos
        fields = [
            "pedi_empr", "pedi_fili", "pedi_clie", "pedi_vend", "pedi_data", "pedi_entr",
            "pedi_obse", "pedi_desc", "pedi_tota", "pedi_stat", "pedi_orca",
        ]
        widgets = {
            "pedi_data": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "pedi_entr": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for _, field in self.fields.items():
            field.widget.attrs.setdefault("class", "form-control")
