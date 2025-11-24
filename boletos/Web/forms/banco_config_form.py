from django import forms
from django.core.exceptions import ValidationError

try:
    from Entidades.models import Entidades
except Exception:
    Entidades = None


# Lista dos principais bancos brasileiros
BANCOS_BRASILEIROS = [
    ('', 'Selecione o banco'),
    ('001', '001 - Banco do Brasil'),
    ('033', '033 - Santander'),
    ('104', '104 - Caixa Econômica Federal'),
    ('237', '237 - Bradesco'),
    ('341', '341 - Itaú'),
    ('748', '748 - Sicredi'),
    ('756', '756 - Sicoob'),
    ('077', '077 - Banco Inter'),
    ('260', '260 - Nubank'),
    ('290', '290 - PagBank'),
    ('212', '212 - Banco Original'),
    ('041', '041 - Banrisul'),
    ('422', '422 - Banco Safra'),
    ('070', '070 - BRB'),
    ('136', '136 - Unicred'),
    ('389', '389 - Banco Mercantil'),
    ('655', '655 - Banco Votorantim'),
    ('623', '623 - Banco PAN'),
    ('633', '633 - Banco Rendimento'),
    ('197', '197 - Stone Pagamentos'),
]


class BancoConfigForm(forms.ModelForm):
    """Formulário profissional para configuração de contas bancárias"""
    
    # Campo customizado para seleção do banco
    codigo_banco = forms.ChoiceField(
        choices=BANCOS_BRASILEIROS,
        required=True,
        label='Banco',
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg',
            'style': 'font-weight: 500;'
        })
    )
    
    logo_variation = forms.ChoiceField(
        choices=[('Colorido', 'Colorido'), ('PretoBranco', 'Preto e Branco')],
        required=False,
        label='Variação do Logo',
        initial='Colorido'
    )

    class Meta:
        model = Entidades
        fields = [
            'enti_nome', 'enti_fant',
            'enti_agen', 'enti_diag',
            'enti_coco', 'enti_dico', 'enti_tien',
            'enti_cep', 'enti_ende', 'enti_nume',
            'enti_cida', 'enti_esta',
        ]
        
        labels = {
            'enti_nome': 'Nome da Conta/Agência',
            'enti_fant': 'Apelido/Identificação',
            'enti_agen': 'Agência',
            'enti_diag': 'Dígito da Agência',
            'enti_coco': 'Conta Corrente',
            'enti_dico': 'Dígito da Conta',
            'enti_tien': 'Tipo de Entidade',
            'enti_cep': 'CEP',
            'enti_ende': 'Endereço',
            'enti_nume': 'Número',
            'enti_cida': 'Cidade',
            'enti_esta': 'Estado (UF)',
        }
        
        widgets = {
            'enti_nome': forms.TextInput(attrs={
                'placeholder': 'Ex: Conta Corrente Principal',
                'autocomplete': 'off'
            }),
            'enti_fant': forms.TextInput(attrs={
                'placeholder': 'Ex: CC Principal',
                'autocomplete': 'off'
            }),
            'enti_agen': forms.TextInput(attrs={
                'placeholder': 'Ex: 1234',
                'maxlength': 10,
                'inputmode': 'numeric'
            }),
            'enti_diag': forms.TextInput(attrs={
                'placeholder': 'Ex: 1',
                'maxlength': 2,
                'inputmode': 'numeric'
            }),
            'enti_coco': forms.TextInput(attrs={
                'placeholder': 'Ex: 12345678',
                'maxlength': 20,
                'inputmode': 'numeric'
            }),
            'enti_dico': forms.TextInput(attrs={
                'placeholder': 'Ex: 9',
                'maxlength': 2,
                'inputmode': 'numeric'
            }),
            'enti_tien': forms.Select(),
            'enti_cep': forms.TextInput(attrs={
                'placeholder': '00000-000',
                'maxlength': 9,
            }),
            'enti_ende': forms.TextInput(attrs={
                'placeholder': 'Rua, Avenida, etc.'
            }),
            'enti_nume': forms.TextInput(attrs={
                'placeholder': 'Nº',
                'maxlength': 10
            }),
            'enti_cida': forms.TextInput(attrs={
                'placeholder': 'Nome da cidade'
            }),
            'enti_esta': forms.TextInput(attrs={
                'placeholder': 'UF',
                'maxlength': 2,
                'style': 'text-transform: uppercase;'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Se está editando, preencher o código do banco
        if self.instance and self.instance.pk and hasattr(self.instance, 'enti_banc'):
            banco_code = str(self.instance.enti_banc).zfill(3) if self.instance.enti_banc else ''
            self.fields['codigo_banco'].initial = banco_code
        
        # Aplicar classes Bootstrap a todos os campos
        for field_name, field in self.fields.items():
            if field_name == 'codigo_banco':
                continue  # Já tem classe definida
            
            current_class = field.widget.attrs.get('class', '')
            if 'form-control' not in current_class and 'form-select' not in current_class:
                field.widget.attrs['class'] = f'{current_class} form-control'.strip()
            
            # Marcar campos obrigatórios
            if field.required:
                field.widget.attrs['required'] = 'required'
        
        # Ajustes específicos
        self.fields['enti_esta'].widget.attrs.update({'class': 'form-control text-uppercase'})
        self.fields['logo_variation'].widget.attrs.update({'class': 'form-select'})
        
        # Tornar campos de endereço opcionais
        self.fields['enti_cep'].required = False
        self.fields['enti_ende'].required = False
        self.fields['enti_nume'].required = False
        self.fields['enti_cida'].required = False
        self.fields['enti_esta'].required = False

    def clean_codigo_banco(self):
        """Valida código do banco selecionado"""
        codigo = self.cleaned_data.get('codigo_banco', '').strip()
        
        if not codigo:
            raise ValidationError('Selecione um banco.')
        
        if not codigo.isdigit():
            raise ValidationError('Código de banco inválido.')
        
        return codigo

    def clean_enti_agen(self):
        agen = self.cleaned_data.get('enti_agen', '').strip()
        if not agen:
            raise ValidationError('A agência é obrigatória.')
        agen_limpo = ''.join(filter(str.isdigit, agen))
        if not agen_limpo:
            raise ValidationError('A agência deve conter números.')
        if len(agen_limpo) > 10:
            raise ValidationError('A agência deve ter no máximo 10 dígitos.')
        return agen_limpo

    def clean_enti_diag(self):
        diag = self.cleaned_data.get('enti_diag', '').strip()
        if diag:
            diag_limpo = ''.join(filter(str.isdigit, diag))
            if len(diag_limpo) > 2:
                raise ValidationError('O dígito verificador da agência deve ter no máximo 2 caracteres.')
            return diag_limpo
        return diag

    def clean_enti_coco(self):
        coco = self.cleaned_data.get('enti_coco', '').strip()
        if not coco:
            raise ValidationError('A conta corrente é obrigatória.')
        coco_limpo = ''.join(filter(str.isdigit, coco))
        if not coco_limpo:
            raise ValidationError('A conta corrente deve conter números.')
        if len(coco_limpo) < 4:
            raise ValidationError('A conta corrente deve ter no mínimo 4 dígitos.')
        if len(coco_limpo) > 20:
            raise ValidationError('A conta corrente deve ter no máximo 20 dígitos.')
        return coco_limpo

    def clean_enti_dico(self):
        dico = self.cleaned_data.get('enti_dico', '').strip()
        if not dico:
            raise ValidationError('O dígito verificador da conta é obrigatório.')
        dico_limpo = dico.upper()
        if not (dico_limpo.isdigit() or dico_limpo == 'X'):
            raise ValidationError('O dígito verificador deve ser numérico ou X.')
        if len(dico_limpo) > 2:
            raise ValidationError('O dígito verificador deve ter no máximo 2 caracteres.')
        return dico_limpo

    def clean_enti_esta(self):
        esta = self.cleaned_data.get('enti_esta', '').strip().upper()
        if esta:
            if len(esta) != 2:
                raise ValidationError('A UF deve conter exatamente 2 caracteres.')
            ufs_validas = [
                'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
                'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
                'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
            ]
            if esta not in ufs_validas:
                raise ValidationError('UF inválida.')
        return esta

    def clean_enti_cep(self):
        cep = self.cleaned_data.get('enti_cep', '').strip()
        if cep:
            cep_limpo = cep.replace('-', '').replace(' ', '')
            if not cep_limpo.isdigit() or len(cep_limpo) != 8:
                raise ValidationError('CEP inválido. Use o formato 00000-000.')
            return f'{cep_limpo[:5]}-{cep_limpo[5:]}'
        return cep

    def clean(self):
        cleaned = super().clean()
        codigo_banco = cleaned.get('codigo_banco')
        if codigo_banco:
            cleaned['enti_banc'] = codigo_banco
        return cleaned
    
    def save(self, commit=True, using='default'):
        """Override save para garantir que enti_banc seja salvo"""
        instance = super().save(commit=False)
        
        # Pegar o código do banco do cleaned_data
        if 'codigo_banco' in self.cleaned_data:
            instance.enti_banc = self.cleaned_data['codigo_banco']
        
        if commit:
            if using:
                instance.save(using=using)
            else:
                instance.save()
        
        return instance