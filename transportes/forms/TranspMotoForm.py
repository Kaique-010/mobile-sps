from django import forms

from Entidades.models import Entidades


class TranspMotoForm(forms.ModelForm):
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
