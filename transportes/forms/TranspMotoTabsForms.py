from django import forms
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory
from django.forms.models import construct_instance

from Entidades.models import Entidades
from transportes.models import MotoristaDadosComplementares, MotoristaDocumento, MotoristasCadastros


class BootstrapModelForm(forms.ModelForm):
    """Base para aplicar classes bootstrap de forma padronizada."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = 'form-control'
            if isinstance(field.widget, (forms.CheckboxInput,)):
                css = 'form-check-input'
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                css = 'form-select'
            current = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f"{current} {css}".strip()


class TranspMotoForm(BootstrapModelForm):
    enti_tien = forms.CharField(
        label='Tipo (T/M)',
        max_length=1,
        widget=forms.TextInput(attrs={'maxlength': 1}),
    )

    class Meta:
        model = Entidades
        fields = [
            'enti_nome', 'enti_fant', 'enti_tien', 'enti_situ', 'enti_cpf', 'enti_cnpj',
            'enti_fone', 'enti_celu', 'enti_emai',
            'enti_cep', 'enti_ende', 'enti_nume', 'enti_bair', 'enti_cida', 'enti_esta', 'enti_comp',
        ]
        labels = {
            'enti_nome': 'Nome',
            'enti_fant': 'Fantasia',
            'enti_situ': 'Situação',
            'enti_cpf': 'CPF',
            'enti_cnpj': 'CNPJ',
            'enti_fone': 'Telefone',
            'enti_celu': 'Celular',
            'enti_emai': 'E-mail',
            'enti_cep': 'CEP',
            'enti_ende': 'Endereço',
            'enti_nume': 'Número',
            'enti_bair': 'Bairro',
            'enti_cida': 'Cidade',
            'enti_esta': 'UF',
            'enti_comp': 'Complemento',
        }
        widgets = {
            'enti_nome': forms.TextInput(attrs={'placeholder': 'Nome completo'}),
            'enti_fant': forms.TextInput(attrs={'placeholder': 'Nome fantasia'}),
            'enti_situ': forms.Select(),
            'enti_cpf': forms.TextInput(attrs={'placeholder': 'Somente números'}),
            'enti_cnpj': forms.TextInput(attrs={'placeholder': 'Somente números'}),
            'enti_emai': forms.EmailInput(attrs={'placeholder': 'email@dominio.com'}),
            'enti_cep': forms.TextInput(attrs={'maxlength': 8}),
            'enti_esta': forms.TextInput(attrs={'maxlength': 2}),
        }

    def clean_enti_tien(self):
        tipo = (self.cleaned_data.get('enti_tien') or '').strip().upper()
        if tipo not in {'T', 'M'}:
            raise forms.ValidationError('Tipo deve ser T (Transportadora) ou M (Motorista).')
        return tipo

    def _post_clean(self):
        opts = self._meta
        exclude = self._get_validation_exclusions()
        if 'enti_tien' not in exclude:
            exclude.append('enti_tien')
        try:
            self.instance = construct_instance(self, self.instance, opts.fields, opts.exclude)
        except ValidationError as e:
            self._update_errors(e)
        try:
            self.instance.full_clean(exclude=exclude, validate_unique=False)
        except ValidationError as e:
            self._update_errors(e)
        if self._validate_unique:
            self.validate_unique()


class MotoristaCadastroForm(BootstrapModelForm):
    class Meta:
        model = MotoristasCadastros
        fields = ['status']
        labels = {'status': 'Status do motorista'}
        widgets = {'status': forms.Select()}


class MotoristaDadosComplementaresForm(BootstrapModelForm):
    class Meta:
        model = MotoristaDadosComplementares
        fields = ['cnh_numero', 'cnh_categoria', 'cnh_validade', 'rg_numero', 'ear', 'ear_validade']
        labels = {
            'cnh_numero': 'Número CNH',
            'cnh_categoria': 'Categoria CNH',
            'cnh_validade': 'Validade CNH',
            'rg_numero': 'RG',
            'ear': 'Exerce atividade remunerada (EAR)',
            'ear_validade': 'Validade EAR',
        }
        widgets = {
            'cnh_validade': forms.DateInput(attrs={'type': 'date'}),
            'ear_validade': forms.DateInput(attrs={'type': 'date'}),
            'ear': forms.CheckboxInput(),
        }


class MotoristaDocumentoForm(BootstrapModelForm):
    class Meta:
        model = MotoristaDocumento
        fields = [
            'tipo_doc', 'numero', 'status', 'data_emissao', 'data_validade',
            'alerta_em_dias', 'observacoes', 'anexos',
        ]
        labels = {
            'tipo_doc': 'Tipo do documento',
            'numero': 'Número',
            'status': 'Status',
            'data_emissao': 'Data de emissão',
            'data_validade': 'Data de validade',
            'alerta_em_dias': 'Alerta (dias)',
            'observacoes': 'Observações',
            'anexos': 'Anexos (referência)',
        }
        widgets = {
            'status': forms.Select(),
            'data_emissao': forms.DateInput(attrs={'type': 'date'}),
            'data_validade': forms.DateInput(attrs={'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'rows': 2}),
            'anexos': forms.Textarea(attrs={'rows': 2}),
        }


MotoristaDocumentoFormSet = modelformset_factory(
    MotoristaDocumento,
    form=MotoristaDocumentoForm,
    extra=1,
    can_delete=True,
)
