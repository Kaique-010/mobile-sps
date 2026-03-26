from django import forms

from transportes.models import Mdfe


class MdfeForm(forms.ModelForm):
    class Meta:
        model = Mdfe
        fields = [
            "mdf_seri",
            "mdf_esta_orig",
            "mdf_esta_dest",
            "mdf_cida_carr",
            "mdf_nome_carr",
            "mdf_tipo_emit",
            "mdf_tipo_tran",
            "mdf_pred_carg",
            "mdf_pred_xprod",
            "mdf_pred_ncm",
            "mdf_pred_ean",
            "mdf_tran",
            "mdf_moto",
            "mdf_veic",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mdf_seri"].required = False
        for name, field in self.fields.items():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)
