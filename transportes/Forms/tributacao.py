from django import forms
from transportes.models import Cte

class CteTributacaoForm(forms.ModelForm):
    class Meta:
        model = Cte
        fields = [
            'cfop', 'cst_icms', 'aliq_icms', 'base_icms', 'reducao_icms', 'valor_icms',
            'cst_pis', 'aliquota_pis', 'base_pis', 'valor_pis',
            'cst_cofins', 'aliquota_cofins', 'base_cofins', 'valor_cofins',
            # IBS e CBS
            'ibscbs_vbc', 'ibscbs_cstid', 'ibscbs_cst', 'ibscbs_cclasstrib',
            'ibs_pdifuf', 'ibs_vdifuf', 'ibs_vdevtribuf', 'ibs_vdevtribmun',
            'cbs_vdevtrib', 'ibs_pibsuf', 'ibs_preduf', 'ibs_paliqefetuf',
            'ibs_vibsuf', 'ibs_pdifmun', 'ibs_vdifmun', 'ibs_pibsmun',
            'ibs_predmun', 'ibs_paliqefetmun', 'ibs_vibsmun', 'ibs_vibs',
            'cbs_pdif', 'cbs_vdif', 'cbs_pcbs', 'cbs_pred', 'cbs_paliqefet',
            'cbs_vcbs', 'ibscbs_cstregid', 'ibscbs_cstreg', 'ibscbs_cclasstribreg',
            'ibs_paliqefetufreg', 'ibs_vtribufreg'
        ]
        widgets = {
            'cfop': forms.NumberInput(attrs={'class': 'form-control'}),
            'cst_icms': forms.TextInput(attrs={'class': 'form-control'}),
            'aliq_icms': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'base_icms': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reducao_icms': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_icms': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cst_pis': forms.TextInput(attrs={'class': 'form-control'}),
            'aliquota_pis': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'base_pis': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_pis': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cst_cofins': forms.TextInput(attrs={'class': 'form-control'}),
            'aliquota_cofins': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'base_cofins': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_cofins': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            # IBS e CBS Widgets (simplified)
            'ibscbs_vbc': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ibscbs_cst': forms.TextInput(attrs={'class': 'form-control'}),
            'ibscbs_cclasstrib': forms.TextInput(attrs={'class': 'form-control'}),
            'ibs_pibsuf': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ibs_vibsuf': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cbs_pcbs': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cbs_vcbs': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            # ... add others if needed explicitly, but standard NumberInput is default for DecimalField in ModelForm?
            # Actually ModelForm defaults are usually okay, but 'form-control' class is nice.
        }
