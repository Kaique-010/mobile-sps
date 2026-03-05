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
            'cst': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '3'}),
            'csosn': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '4'}),
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
