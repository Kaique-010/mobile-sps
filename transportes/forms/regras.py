from django import forms
from transportes.models import RegraICMS
from CFOP.models import CFOP
from core.utils import get_licenca_db_config

ESTADOS_CHOICES = [
    ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
    ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'),
    ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'),
    ('MG', 'Minas Gerais'), ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'),
    ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
    ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'),
    ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins'),
    ('EX', 'Exterior')
]

CST_CHOICES = [
    ("", "---------"),
    ("00", "00 - Tributada integralmente"),
    ("10", "10 - Tributada com cobrança de ICMS por ST"),
    ("20", "20 - Com redução de base de cálculo"),
    ("30", "30 - Isenta/não tributada com cobrança de ICMS por ST"),
    ("40", "40 - Isenta"),
    ("41", "41 - Não tributada"),
    ("50", "50 - Suspensão"),
    ("51", "51 - Diferimento"),
    ("60", "60 - ICMS cobrado anteriormente por ST"),
    ("70", "70 - Redução de base com cobrança por ST"),
    ("90", "90 - Outros"),
]

CSOSN_CHOICES = [
    ("", "---------"),
    ("101", "101 - Tributada com permissão de crédito"),
    ("102", "102 - Tributada sem permissão de crédito"),
    ("103", "103 - Isenção no SN para faixa de receita"),
    ("201", "201 - Tributada com crédito e com ST"),
    ("202", "202 - Tributada sem crédito e com ST"),
    ("203", "203 - Isenção no SN para faixa e com ST"),
    ("300", "300 - Imune"),
    ("400", "400 - Não tributada pelo SN"),
    ("500", "500 - ICMS cobrado anteriormente por ST"),
    ("900", "900 - Outros"),
]

class RegraICMSForm(forms.ModelForm):
    cfop = forms.ModelChoiceField(
        queryset=CFOP.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='CFOP (Opcional)'
    )
    
    uf_origem = forms.ChoiceField(
        choices=ESTADOS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    uf_destino = forms.ChoiceField(
        choices=ESTADOS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    cst = forms.ChoiceField(
        choices=CST_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="CST",
    )

    csosn = forms.ChoiceField(
        choices=CSOSN_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="CSOSN (Simples)",
    )

    class Meta:
        model = RegraICMS
        fields = '__all__'
        widgets = {
            'aliquota': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'aliquota_destino': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reducao_base': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'mva_st': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'aliquota_st': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reducao_base_st': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'contribuinte': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'simples_nacional': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'diferimento': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'isento': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Configura queryset do CFOP baseado no banco do tenant
        if self.request:
            db_alias = get_licenca_db_config(self.request)
            self.fields['cfop'].queryset = CFOP.objects.using(db_alias).all().order_by('cfop_codi')
        elif self.instance and self.instance.pk:
            # Tenta pegar do state se não tiver request (fallback)
            db_alias = self.instance._state.db or 'default'
            self.fields['cfop'].queryset = CFOP.objects.using(db_alias).all().order_by('cfop_codi')
        else:
             # Fallback final para default se nada mais funcionar, mas idealmente request deve ser passado
             self.fields['cfop'].queryset = CFOP.objects.using('default').all().order_by('cfop_codi')
        
        # Set initial value for CFOP if instance exists
        if self.instance and self.instance.pk and self.instance.cfop:
            # Pega o alias do queryset configurado acima
            db_alias = self.fields['cfop'].queryset.db
            try:
                cfop_obj = CFOP.objects.using(db_alias).filter(cfop_codi=self.instance.cfop).first()
                if cfop_obj:
                    self.initial['cfop'] = cfop_obj
            except Exception:
                pass

        is_simples = bool(self.instance.simples_nacional) if getattr(self.instance, "pk", None) else False
        if self.data:
            is_simples = self.data.get("simples_nacional") in {"on", "true", "True", "1"}

        self.fields["csosn"].required = is_simples
        self.fields["cst"].required = not is_simples

    def clean_cfop(self):
        cfop = self.cleaned_data.get('cfop')
        # Se for ModelChoiceField, cfop já é o objeto ou None
        # Precisamos retornar o ID ou string que o model espera, ou o próprio objeto se o model suportar
        # O model RegraICMS tem cfop como CharField ou IntegerField? 
        # No código anterior era TextInput com maxlength 4, indicando que pode ser string.
        # Mas o model CFOP tem cfop_codi. 
        # Vamos verificar o model RegraICMS novamente.
        # Se o model espera o código (ex: '5102'), devemos retornar cfop.cfop_codi
        if cfop:
            return cfop.cfop_codi
        return None

    def clean(self):
        cleaned_data = super().clean()
        is_simples = bool(cleaned_data.get("simples_nacional"))

        if is_simples:
            csosn = (cleaned_data.get("csosn") or "").strip()
            if not csosn:
                self.add_error("csosn", "Informe o CSOSN.")
            cst = (cleaned_data.get("cst") or "").strip()
            cleaned_data["cst"] = cst or "00"
        else:
            cst = (cleaned_data.get("cst") or "").strip()
            if not cst:
                self.add_error("cst", "Informe o CST.")
            cleaned_data["csosn"] = None

        return cleaned_data
