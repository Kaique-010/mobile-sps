from django import forms


class ColetaLeituraForm(forms.Form):
    codigo_barras = forms.CharField(label='Código de Barras', max_length=50)
    quantidade = forms.DecimalField(label='Quantidade Lida', max_digits=10, decimal_places=2, min_value=0.01)
