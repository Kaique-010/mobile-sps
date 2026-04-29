from django import forms
from django.forms import formset_factory

from Pisos.models import Pedidospisos


class PedidoPisosForm(forms.ModelForm):
    class Meta:
        model = Pedidospisos
        fields = [
            "pedi_empr", "pedi_fili", "pedi_clie", "pedi_forn", "pedi_vend", "pedi_data",
            "pedi_data_prev_entr", "pedi_data_inst", "pedi_data_entr_inst", "pedi_orca", "pedi_stat",
            "pedi_form_paga", "pedi_desc", "pedi_fret", "pedi_tota", "pedi_obse", "pedi_croq_info",
            "pedi_mode_piso", "pedi_mode_alum", "pedi_mode_roda", "pedi_mode_port", "pedi_mode_outr",
            "pedi_sent_piso", "pedi_ajus_port", "pedi_degr_esca", "pedi_obra_habi", "pedi_movi_mobi",
            "pedi_remo_roda", "pedi_remo_carp",
        ]
        widgets = {k: forms.DateInput(attrs={"type": "date", "class": "form-control"}) for k in [
            "pedi_data", "pedi_data_prev_entr", "pedi_data_inst", "pedi_data_entr_inst"
        ]}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for _, field in self.fields.items():
            css = "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else "form-control"
            field.widget.attrs.setdefault("class", css)


class ItemPedidoPisosForm(forms.Form):
    item_ambi = forms.IntegerField(required=False)
    item_nome_ambi = forms.CharField(required=False, max_length=100)
    item_prod = forms.CharField(max_length=20)
    item_prod_nome = forms.CharField(required=False, max_length=100)
    item_m2 = forms.DecimalField(required=False, decimal_places=4, max_digits=15)
    item_quan = forms.DecimalField(required=False, decimal_places=4, max_digits=15)
    item_caix = forms.IntegerField(required=False)
    item_unit = forms.DecimalField(required=False, decimal_places=4, max_digits=15)
    item_desc = forms.DecimalField(required=False, decimal_places=4, max_digits=15)
    item_queb = forms.DecimalField(required=False, decimal_places=2, max_digits=5)
    item_obse = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 1}))


ItemPedidoPisosFormSet = formset_factory(ItemPedidoPisosForm, extra=1, can_delete=True)
