from django import forms
from transportes.models import Cte

class CteEmissaoForm(forms.ModelForm):
    class Meta:
        model = Cte
        fields = [
            "remetente",
            "destinatario",
            "motorista",
            "veiculo",
            "tomador_servico",
            "tipo_servico",
            "tipo_cte",
            "forma_emissao",
            "tipo_frete",
        ]
        widgets = {
            'emissao': forms.DateInput(attrs={'type': 'date'}),
            'hora': forms.TimeInput(attrs={'type': 'time'}),
            'remetente': forms.HiddenInput(),
            'destinatario': forms.HiddenInput(),
            'motorista': forms.HiddenInput(),
            'veiculo': forms.HiddenInput(),
            'tomador_servico': forms.RadioSelect(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'tipo_servico': forms.RadioSelect(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'tipo_cte': forms.RadioSelect(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'forma_emissao': forms.RadioSelect(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'tipo_frete': forms.RadioSelect(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        # Validações básicas de formulário aqui
        # Regras fiscais complexas devem ir para o ValidacaoService
        return cleaned_data
