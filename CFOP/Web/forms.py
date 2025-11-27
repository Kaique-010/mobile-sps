from django import forms
from ..models import CFOP

class CFOPForm(forms.ModelForm):
    
    class Meta:
        model = CFOP
        fields = [
            "cfop_empr",
            "cfop_codi",
            "cfop_desc",

            "cfop_exig_icms",
            "cfop_exig_ipi",
            "cfop_exig_pis_cofins",
            "cfop_exig_cbs",
            "cfop_exig_ibs",

            "cfop_gera_st",
            "cfop_gera_difal",
        ]

        widgets = {
            "cfop_empr": forms.HiddenInput(),
            "cfop_codi": forms.TextInput(attrs={"class": "form-control"}),
            "cfop_desc": forms.TextInput(attrs={"class": "form-control"}),

            "cfop_exig_icms": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "cfop_exig_ipi": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "cfop_exig_pis_cofins": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "cfop_exig_cbs": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "cfop_exig_ibs": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "cfop_gera_st": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "cfop_gera_difal": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, regime=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.regime = regime
