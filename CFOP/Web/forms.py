from django import forms
from Produtos.models import Ncm
from ..models import CFOP, NcmFiscalPadrao
class CFOPForm(forms.ModelForm):
    class Meta:
        model = CFOP
        fields = [
            "cfop_empr", "cfop_codi", "cfop_desc",
            "cfop_exig_icms", "cfop_exig_ipi", "cfop_exig_pis_cofins",
            "cfop_exig_cbs", "cfop_exig_ibs",
            "cfop_gera_st", "cfop_gera_difal",
            "cfop_icms_base_inclui_ipi", "cfop_st_base_inclui_ipi",
            "cfop_ipi_tota_nf", "cfop_st_tota_nf",
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
            "cfop_icms_base_inclui_ipi": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "cfop_st_base_inclui_ipi": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "cfop_ipi_tota_nf": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "cfop_st_tota_nf": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, regime=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.regime = regime


class NCMFiscalPadraoForm(forms.ModelForm):
    class Meta:
        model = NcmFiscalPadrao
        fields = [
            'ncm',
            'cst_icms', 'aliq_icms',
            'cst_ipi', 'aliq_ipi',
            'cst_pis', 'aliq_pis',
            'cst_cofins', 'aliq_cofins',
            'cst_cbs', 'aliq_cbs',
            'cst_ibs', 'aliq_ibs',
        ]
        widgets = {
            'ncm': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código NCM', 'list': 'ncm-codes'}),
            'cst_icms': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CST ICMS'}),
            'aliq_icms': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Aliq ICMS'}),
            'cst_ipi': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CST IPI'}),
            'aliq_ipi': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Aliq IPI'}),
            'cst_pis': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CST PIS'}),
            'aliq_pis': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Aliq PIS'}),
            'cst_cofins': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CST COFINS'}),
            'aliq_cofins': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Aliq COFINS'}),
            'cst_cbs': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CST CBS'}),
            'aliq_cbs': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Aliq CBS'}),
            'cst_ibs': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CST IBS'}),
            'aliq_ibs': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Aliq IBS'}),
        }
    
    def clean_ncm(self):
        ncm_input = self.cleaned_data.get('ncm')
        if not ncm_input:
            return None
            
        if isinstance(ncm_input, Ncm):
            return ncm_input
            
        # Remove formatting and description if present
        # Format expectation: "12345678" or "12345678 - Description"
        code = str(ncm_input).split(' - ')[0].strip()
        
        # Primeiro tenta buscar no banco de NCMs (prioridade)
        obj = Ncm.objects.using(self.ncm_database).filter(ncm_codi=code).first()
        
        # Se não encontrar, tenta no banco local (fallback)
        if not obj:
            obj = Ncm.objects.using(self.database).filter(ncm_codi=code).first()
            
        if not obj:
            raise forms.ValidationError(f"NCM '{code}' não encontrado.")
            
        # Valida se já existe regra para este NCM
        # A validação de unicidade deve ser feita no banco onde a regra será salva (self.database)
        qs = NcmFiscalPadrao.objects.using(self.database).filter(ncm_id=obj.ncm_codi)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise forms.ValidationError(f"Já existe uma regra fiscal padrão para o NCM {code}. Edite a regra existente.")

        return obj

    def __init__(self, *args, **kwargs):
        cst_choices = kwargs.pop('cst_choices', None)
        self.database = kwargs.pop('database', 'default')
        self.ncm_database = kwargs.pop('ncm_database', self.database)
        super().__init__(*args, **kwargs)

        # Force ncm to be a CharField to allow custom cleaning of "CODE - DESC" format
        self.fields['ncm'] = forms.CharField(
            widget=forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Digite o código ou descrição',
                'autocomplete': 'off'
            }),
            required=True
        )
        
        if self.instance and getattr(self.instance, 'ncm_id', None):
             # Pre-fill with code if editing
             try:
                 # Ensure we have the ncm object loaded
                 ncm_obj = self.instance.ncm
                 self.initial['ncm'] = f"{ncm_obj.ncm_codi} - {ncm_obj.ncm_desc}"
             except:
                 self.initial['ncm'] = self.instance.ncm_id

        if cst_choices:
            if 'icms' in cst_choices:
                self.fields['cst_icms'].widget = forms.Select(
                    choices=[('', '--- Selecione ---')] + cst_choices['icms'], 
                    attrs={'class': 'form-select'}
                )
            if 'ipi' in cst_choices:
                self.fields['cst_ipi'].widget = forms.Select(
                    choices=[('', '--- Selecione ---')] + cst_choices['ipi'], 
                    attrs={'class': 'form-select'}
                )
            if 'pis' in cst_choices:
                self.fields['cst_pis'].widget = forms.Select(
                    choices=[('', '--- Selecione ---')] + cst_choices['pis'], 
                    attrs={'class': 'form-select'}
                )
            if 'cofins' in cst_choices:
                self.fields['cst_cofins'].widget = forms.Select(
                    choices=[('', '--- Selecione ---')] + cst_choices['cofins'], 
                    attrs={'class': 'form-select'}
                )
            if 'ibs' in cst_choices:
                self.fields['cst_ibs'].widget = forms.Select(
                    choices=[('', '--- Selecione ---')] + cst_choices['ibs'], 
                    attrs={'class': 'form-select'}
                )
            if 'cbs' in cst_choices:
                self.fields['cst_cbs'].widget = forms.Select(
                    choices=[('', '--- Selecione ---')] + cst_choices['cbs'], 
                    attrs={'class': 'form-select'}
                )

        # Make all fields optional as they are overrides
        for field in self.fields:
            if field != 'ncm':
                self.fields[field].required = False

    def clean_ncm(self):
        ncm_input = self.cleaned_data.get('ncm')
        if not ncm_input:
            return None
            
        if isinstance(ncm_input, Ncm):
            return ncm_input
            
        # Remove formatting and description if present
        # Format expectation: "12345678" or "12345678 - Description"
        code = str(ncm_input).split(' - ')[0].strip()
        
        # Primeiro tenta buscar no banco de NCMs (prioridade)
        obj = Ncm.objects.using(self.ncm_database).filter(ncm_codi=code).first()
        
        # Se não encontrar, tenta no banco local (fallback)
        if not obj:
            obj = Ncm.objects.using(self.database).filter(ncm_codi=code).first()
            
        if not obj:
            raise forms.ValidationError(f"NCM '{code}' não encontrado.")
            
        # Valida se já existe regra para este NCM
        # A validação de unicidade deve ser feita no banco onde a regra será salva (self.database)
        qs = NcmFiscalPadrao.objects.using(self.database).filter(ncm_id=obj.ncm_codi)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise forms.ValidationError(f"Já existe uma regra fiscal padrão para o NCM {code}. Edite a regra existente.")

        return obj
