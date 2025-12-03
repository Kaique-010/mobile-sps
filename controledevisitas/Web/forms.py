from django import forms


class ItemVisitaForm(forms.Form):
    produto_codigo = forms.CharField(label='Código do Produto', max_length=60)
    quantidade = forms.DecimalField(label='Quantidade', max_digits=15, decimal_places=5)
    valor_unitario = forms.DecimalField(label='Valor Unitário', max_digits=15, decimal_places=5, required=False)
    observacoes = forms.CharField(label='Observações', required=False, widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' form-control').strip()


class ControleVisitaForm(forms.Form):
    ctrl_data = forms.DateField(label='Data da Visita', widget=forms.DateInput(attrs={'type': 'date'}))
    ctrl_cliente_id = forms.IntegerField(label='Cliente ID')
    ctrl_vendedor_id = forms.IntegerField(label='Vendedor ID', required=False)
    ctrl_etapa_id = forms.IntegerField(label='Etapa ID', required=False)
    ctrl_contato = forms.CharField(label='Contato', max_length=50, required=False)
    ctrl_fone = forms.CharField(label='Telefone', max_length=50, required=False)
    ctrl_obse = forms.CharField(label='Observações', widget=forms.Textarea, required=False)
    ctrl_prox_visi = forms.DateField(label='Próxima Visita', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    ctrl_km_inic = forms.DecimalField(label='KM Inicial', max_digits=15, decimal_places=2, required=False)
    ctrl_km_fina = forms.DecimalField(label='KM Final', max_digits=15, decimal_places=2, required=False)
    ctrl_novo = forms.BooleanField(label='Novo Cliente', required=False)
    ctrl_base = forms.BooleanField(label='Base', required=False)
    ctrl_prop = forms.BooleanField(label='Proposta', required=False)
    ctrl_leva = forms.BooleanField(label='Levantamento', required=False)
    ctrl_proj = forms.IntegerField(label='Projeto', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = (css + ' form-check-input').strip()
            else:
                field.widget.attrs['class'] = (css + ' form-control').strip()
