from django import forms
from django.core.exceptions import ValidationError
from ...models import Carteira

CNAB_CHOICES = [
    ('240', 'CNAB 240'),
    ('400', 'CNAB 400'),
]

class CarteiraForm(forms.ModelForm):
    class Meta:
        model = Carteira
        fields = [
            'cart_codi', 'cart_nome', 'cart_conv', 'cart_cart', 'cart_noss_nume',
            'cart_cnab', 'cart_mult', 'cart_juro', 'cart_desc',
            'cart_codi_tran', 'cart_codi_cede',
            'cart_webs_clie_id', 'cart_webs_clie_secr', 'cart_webs_user_key',
            'cart_webs_scop', 'cart_webs_indi_pix', 'cart_webs_chav_pix',
            'cart_webs_crt', 'cart_webs_key', 'cart_mens_loca','cart_espe_moed',
            'cart_espe', 'cart_acei', 'cart_nume_arqu', 'cart_bole', 'cart_tipo_docu', 'cart_baix', 'cart_prot', 'cart_nega'
        ]

        widgets = {
            'cart_codi': forms.NumberInput(attrs={'class': 'form-control', 'min': 1,'placeholder':'Código da Carteira'}),
            'cart_nome': forms.TextInput(attrs={'class': 'form-control','placeholder':'Nome da Carteira'}),
            'cart_conv': forms.TextInput(attrs={'class': 'form-control','placeholder':'Convênio'}),
            'cart_cart': forms.TextInput(attrs={'class': 'form-control','placeholder':'Código do Carteira'}),
            'cart_noss_nume': forms.TextInput(attrs={'class': 'form-control','placeholder':'Número da Carteira'}),
            'cart_cnab': forms.Select(choices=CNAB_CHOICES, attrs={'class': 'form-select','placeholder':'CNAB 240 ou 400'}),
            'cart_mult': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01','placeholder':'Múltiplo'}),
            'cart_juro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001','placeholder':'Juros'}),
            'cart_desc': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01','placeholder':'Desconto'}),
            'cart_mens_loca': forms.TextInput(attrs={'class': 'form-control','placeholder':'Mensagem'}),
            'cart_codi_tran': forms.TextInput(attrs={'class': 'form-control','placeholder':'Código de Transação'}),
            'cart_codi_cede': forms.TextInput(attrs={'class': 'form-control','placeholder':'Código do Cedente'}),
            'cart_webs_clie_id': forms.TextInput(attrs={'class': 'form-control','placeholder':'ID do Cliente'}),
            'cart_webs_clie_secr': forms.TextInput(attrs={'class': 'form-control','placeholder':'Segredo do Cliente'}),
            'cart_webs_user_key': forms.TextInput(attrs={'class': 'form-control','placeholder':'Chave do Usuário'}),
            'cart_webs_scop': forms.TextInput(attrs={'class': 'form-control','placeholder':'Escopo'}),
            'cart_webs_indi_pix': forms.CheckboxInput(attrs={'class': 'form-check-input','placeholder':'Indica se é PIX'}),
            'cart_webs_chav_pix': forms.TextInput(attrs={'class': 'form-control','placeholder':'Chave PIX'}),
            'cart_webs_crt': forms.TextInput(attrs={'class': 'form-control','placeholder':'Certificado'}),
            'cart_webs_key': forms.TextInput(attrs={'class': 'form-control','placeholder':'Chave'}),
            'cart_espe': forms.TextInput(attrs={'class': 'form-control','placeholder':'Espécie da Moeda'}),
            'cart_espe_moed': forms.TextInput(attrs={'class': 'form-control','placeholder':'Moeda'}),
            'cart_acei': forms.NumberInput(attrs={'class': 'form-control','placeholder':'Aceite'}),
            'cart_nume_arqu': forms.NumberInput(attrs={'class': 'form-control','placeholder':'Número do Arquivo'}),
            'cart_bole': forms.NumberInput(attrs={'class': 'form-control','placeholder':'Boleto'}),
            'cart_tipo_docu': forms.NumberInput(attrs={'class': 'form-control','placeholder':'Tipo de Documento'}),
            'cart_baix': forms.NumberInput(attrs={'class': 'form-control','placeholder':'Baixar'}),
            'cart_prot': forms.NumberInput(attrs={'class': 'form-control','placeholder':'Protestar'}),
            'cart_nega': forms.TextInput(attrs={'class': 'form-control','placeholder':'Negativar'}),
        }

    def __init__(self, *args, **kwargs):
        self.database = kwargs.pop('database', None)
        self.empresa_id = kwargs.pop('empresa_id', None)
        self.filial_id = kwargs.pop('filial_id', None)
        self.banco_codigo = kwargs.pop('banco_codigo', None)
        super().__init__(*args, **kwargs)
        # Campos obrigatórios mínimos
        self.fields['cart_nome'].required = True
        self.fields['cart_cart'].required = True
        if not getattr(self.instance, 'pk', None):
            if self.database and self.empresa_id and self.banco_codigo:
                self.fields['cart_codi'].initial = Carteira.next_code(self.banco_codigo, self.empresa_id, filial=self.filial_id, using=self.database)
        else:
            self.fields['cart_codi'].widget.attrs['readonly'] = 'readonly'

    def clean_cart_codi(self):
        # Em edição, tratar como PATCH: não alterar o código
        if getattr(self.instance, 'pk', None):
            return getattr(self.instance, 'cart_codi', int(self.cleaned_data.get('cart_codi') or 0))
        codi = int(self.cleaned_data.get('cart_codi') or 0)
        if codi <= 0:
            raise ValidationError('Código inválido.')
        if self.database and self.empresa_id and self.banco_codigo:
            exists = Carteira.objects.using(self.database).filter(
                cart_empr=self.empresa_id,
                cart_banc=self.banco_codigo,
                cart_codi=codi
            )
            if self.filial_id is not None:
                exists = exists.filter(cart_fili=self.filial_id)
            if exists.exists():
                raise ValidationError('Código já utilizado para este banco.')
        return codi

    def clean_cart_cnab(self):
        cnab = self.cleaned_data.get('cart_cnab')
        if cnab in (None, ''):
            return cnab
        try:
            cnab_int = int(cnab)
            if cnab_int < 0:
                raise ValidationError('CNAB deve ser um inteiro não negativo.')
            return cnab_int
        except (TypeError, ValueError):
            raise ValidationError('CNAB inválido.')

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.empresa_id is not None:
            try:
                obj.cart_empr = int(self.empresa_id)
            except Exception:
                obj.cart_empr = self.empresa_id
        if self.filial_id is not None:
            try:
                obj.cart_fili = int(self.filial_id)
            except Exception:
                obj.cart_fili = self.filial_id
        if self.banco_codigo is not None:
            try:
                obj.cart_banc = int(self.banco_codigo)
            except Exception:
                obj.cart_banc = self.banco_codigo
        # Em edição, garantir que o código não será alterado
        if getattr(self.instance, 'pk', None):
            try:
                obj.cart_codi = int(getattr(self.instance, 'cart_codi', obj.cart_codi))
            except Exception:
                obj.cart_codi = getattr(self.instance, 'cart_codi', obj.cart_codi)
        if commit:
            # Em criação, garantir INSERT e evitar colisão silenciosa com PK incorreta no ORM
            creating = not getattr(self.instance, 'pk', None)
            if creating:
                exists = Carteira.objects.using(self.database or 'default').filter(
                    cart_empr=obj.cart_empr,
                    cart_banc=obj.cart_banc,
                    cart_codi=obj.cart_codi,
                )
                if obj.cart_fili is not None:
                    exists = exists.filter(cart_fili=obj.cart_fili)
                if exists.exists():
                    raise ValidationError({'cart_codi': ['Código já utilizado para este banco.']})
                if self.database:
                    obj.save(using=self.database, force_insert=True)
                else:
                    obj.save(force_insert=True)
            else:
                if self.database:
                    obj.save(using=self.database)
                else:
                    obj.save()
        return obj
