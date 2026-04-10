from django import forms

from TrocasDevolucoes.models import TrocaDevolucao


class TrocaDevolucaoForm(forms.ModelForm):
    class Meta:
        model = TrocaDevolucao
        fields = [
            'tdvl_pdor', 'tdvl_clie', 'tdvl_vend',
            'tdvl_data', 'tdvl_tipo', 'tdvl_stat', 'tdvl_tode', 'tdvl_tore',
            'tdvl_safi', 'tdvl_obse'
        ]
        labels = {
            'tdvl_pdor': 'Pedido de Origem',
            'tdvl_clie': 'Cliente',
            'tdvl_vend': 'Vendedor',
            'tdvl_data': 'Data',
            'tdvl_tipo': 'Tipo',
            'tdvl_stat': 'Status',
            'tdvl_tode': 'Total Devolvido',
            'tdvl_tore': 'Total Reposição',
            'tdvl_safi': 'Saldo Final',
            'tdvl_obse': 'Observações',
        }
        widgets = {
            'tdvl_data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tdvl_tipo': forms.Select(attrs={'class': 'form-select'}),
            'tdvl_stat': forms.Select(attrs={'class': 'form-select'}),
            'tdvl_pdor': forms.NumberInput(attrs={'class': 'form-control'}),
            'tdvl_clie': forms.TextInput(attrs={'class': 'form-control'}),
            'tdvl_vend': forms.TextInput(attrs={'class': 'form-control'}),
            'tdvl_tode': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
            'tdvl_tore': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
            'tdvl_safi': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
            'tdvl_obse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
