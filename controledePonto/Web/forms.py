from django import forms


class RegistroPontoForm(forms.Form):
    colaborador_id = forms.IntegerField(label='Colaborador ID', min_value=1)
    tipo = forms.ChoiceField(choices=[('ENTRADA', 'Entrada'), ('SAIDA', 'Saída')])
