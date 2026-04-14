from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import construct_instance

from Entidades.models import Entidades


class TranspMotoForm(forms.ModelForm):
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
