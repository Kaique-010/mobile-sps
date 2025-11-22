from django import forms

try:
    from Entidades.models import Entidades
except Exception:
    Entidades = None


class BancoConfigForm(forms.ModelForm):
    logo_variation = forms.ChoiceField(choices=[('Colorido', 'Colorido'), ('PretoBranco', 'Preto e Branco')], required=False)

    class Meta:
        model = Entidades
        fields = [
            'enti_banc', 'enti_agen', 'enti_diag', 'enti_coco', 'enti_dico',
            'enti_care', 'enti_core', 'enti_dcre'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control'})

        # Atributos e padrões visuais
        self.fields['enti_banc'].widget.attrs.update({'maxlength': 3, 'pattern': r'\d{3}', 'placeholder': 'Código do banco (3 dígitos)'} )
        self.fields['enti_agen'].widget.attrs.update({'maxlength': 15, 'pattern': r'\d+', 'placeholder': 'Agência'} )
        self.fields['enti_diag'].widget.attrs.update({'maxlength': 2, 'pattern': r'\d{1,2}', 'placeholder': 'DV Agência'} )
        self.fields['enti_coco'].widget.attrs.update({'maxlength': 15, 'pattern': r'\d+', 'placeholder': 'Conta'} )
        self.fields['enti_dico'].widget.attrs.update({'maxlength': 2, 'pattern': r'\d{1,2}', 'placeholder': 'DV Conta'} )
        self.fields['enti_care'].widget.attrs.update({'maxlength': 10, 'placeholder': 'Carteira'} )

    def clean(self):
        cleaned = super().clean()
        banc = cleaned.get('enti_banc') or ''
        agen = cleaned.get('enti_agen') or ''
        coco = cleaned.get('enti_coco') or ''
        if len(str(banc)) != 3 or not str(banc).isdigit():
            self.add_error('enti_banc', 'Informe o código do banco com 3 dígitos')
        if agen and not str(agen).isdigit():
            self.add_error('enti_agen', 'Agência deve ser numérica')
        if coco and not str(coco).isdigit():
            self.add_error('enti_coco', 'Conta deve ser numérica')
        return cleaned
