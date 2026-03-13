from django import forms


class GerarSpedForm(forms.Form):
    data_inicio = forms.DateField(input_formats=["%Y-%m-%d", "%d/%m/%Y"])
    data_fim = forms.DateField(input_formats=["%Y-%m-%d", "%d/%m/%Y"])
    cod_receita = forms.CharField(required=False, max_length=20)
    data_vencimento = forms.DateField(required=False, input_formats=["%Y-%m-%d", "%d/%m/%Y"])
