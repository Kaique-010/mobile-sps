from django import forms

from django.apps import apps
from ..models import Etapa, Moveetapa, Ordemproducao, Ordemproducaoproduto, Ourives


class OrdemproducaoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dt_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S']
        for field_name in ['orpr_entr', 'orpr_prev']:
            if field_name in self.fields:
                self.fields[field_name].input_formats = dt_formats

    def clean_orpr_entr(self):
        v = self.cleaned_data.get("orpr_entr")
        if v and v.year < 2000:
            raise forms.ValidationError("A data de entrada deve ser a partir do ano 2000.")
        return v

    def clean_orpr_prev(self):
        v = self.cleaned_data.get("orpr_prev")
        if v and v.year < 2000:
            raise forms.ValidationError("A data de previsão deve ser a partir do ano 2000.")
        return v

    class Meta:
        model = Ordemproducao
        fields = [
            'orpr_nuca',
            'orpr_tipo',
            'orpr_clie',
            'orpr_entr',
            'orpr_prev',
            'orpr_vend',
            'orpr_gara',
            'orpr_cort',
            'orpr_valo',
            'orpr_desc',
            'orpr_prod',
            'orpr_quan',
            'orpr_gram_clie',
            'orpr_stat',
        ]
        widgets = {
            'orpr_nuca': forms.TextInput(attrs={'class': 'form-control'}),
            'orpr_tipo': forms.Select(attrs={'class': 'form-select'}),
            'orpr_clie': forms.HiddenInput(),
            'orpr_entr': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'orpr_prev': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'orpr_desc': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'orpr_prod': forms.HiddenInput(),
            'orpr_gara': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'orpr_cort': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'orpr_quan': forms.NumberInput(attrs={'class': 'form-control'}),
            'orpr_gram_clie': forms.NumberInput(attrs={'class': 'form-control'}),
            'orpr_stat': forms.Select(attrs={'class': 'form-select'}),
            'orpr_valo': forms.NumberInput(attrs={'class': 'form-control'}),
            'orpr_vend': forms.HiddenInput(),
        }
        labels = {
            'orpr_nuca': 'Número do cartão',
            'orpr_tipo': 'Tipo',
            'orpr_clie': 'Cliente',
            'orpr_entr': 'Entrada',
            'orpr_prev': 'Previsão',
            'orpr_vend': 'Vendedor(a)',
            'orpr_gara': 'Garantia ?',
            'orpr_cort': 'Cortesia ?',
            'orpr_valo': 'Valor',
            'orpr_desc': 'Descrição',
            'orpr_prod': 'Produto',
            'orpr_quan': 'Quantidade',
            'orpr_gram_clie': 'Gramas do Cliente',
            'orpr_stat': 'Status',
        }


class OurivesForm(forms.ModelForm):
    class Meta:
        model = Ourives
        fields = ["ouri_nome", "ouri_cpfe", "ouri_situ"]
        widgets = {
            "ouri_nome": forms.TextInput(attrs={"class": "form-control"}),
            "ouri_cpfe": forms.TextInput(attrs={"class": "form-control"}),
            "ouri_situ": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "ouri_nome": "Nome",
            "ouri_cpfe": "CPF",
            "ouri_situ": "Ativo ?",
        }


class EtapaForm(forms.ModelForm):
    class Meta:
        model = Etapa
        fields = ["etap_nome", "etap_situ", "etap_obse", "etap_resa", "etap_comi", "etap_ence"]
        widgets = {
            "etap_nome": forms.TextInput(attrs={"class": "form-control"}),
            "etap_situ": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "etap_obse": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "etap_resa": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "etap_comi": forms.Select(attrs={"class": "form-select"}),
            "etap_ence": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "etap_nome": "Nome",
            "etap_situ": "Ativa ?",
            "etap_obse": "Observação",
            "etap_resa": "Retorna Saldo",
            "etap_comi": "Comissão",
            "etap_ence": "Encerra Ordem",
        }


class OrdemProdutoPrevForm(forms.ModelForm):
    def __init__(self, *args, banco="default", empresa_id=1, **kwargs):
        super().__init__(*args, **kwargs)
        ProdutosModel = apps.get_model("Produtos", "Produtos")
        self.fields["orpr_prod_prod"] = forms.ModelChoiceField(
            queryset=ProdutosModel.objects.using(banco).filter(prod_empr=str(empresa_id)).order_by("prod_nome"),
            widget=forms.HiddenInput(),
            label="Matéria-prima",
        )

    class Meta:
        model = Ordemproducaoproduto
        fields = ["orpr_quan_prev"]
        widgets = {
            "orpr_quan_prev": forms.NumberInput(attrs={"class": "form-control"}),
        }
        labels = {
            "orpr_quan_prev": "Quantidade prevista",
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        produto = self.cleaned_data.get("orpr_prod_prod")
        if produto:
            instance.orpr_prod_prod = produto
        if commit:
            instance.save()
        return instance


class MoveetapaForm(forms.ModelForm):
    def __init__(self, *args, banco="default", empresa_id=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["moet_etap"].queryset = Etapa.objects.using(banco).all().order_by("etap_nome")
        self.fields["moet_ouri"].queryset = Ourives.objects.using(banco).filter(ouri_empr=int(empresa_id)).order_by("ouri_nome")
        dt_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"]
        for field_name in ["moet_dain", "moet_dafi"]:
            if field_name in self.fields:
                self.fields[field_name].input_formats = dt_formats

    def clean_moet_dain(self):
        v = self.cleaned_data.get("moet_dain")
        if v and v.year < 2000:
            raise forms.ValidationError("A data de início deve ser a partir do ano 2000.")
        return v

    def clean_moet_dafi(self):
        v = self.cleaned_data.get("moet_dafi")
        if v and v.year < 2000:
            raise forms.ValidationError("A data de fim deve ser a partir do ano 2000.")
        return v

    class Meta:
        model = Moveetapa
        fields = ["moet_etap", "moet_ouri", "moet_dain", "moet_dafi", "moet_peso", "moet_situ", "moet_obse"]
        widgets = {
            "moet_etap": forms.Select(attrs={"class": "form-select"}),
            "moet_ouri": forms.Select(attrs={"class": "form-select"}),
            "moet_dain": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local", "class": "form-control"}),
            "moet_dafi": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local", "class": "form-control"}),
            "moet_peso": forms.NumberInput(attrs={"class": "form-control"}),
            "moet_situ": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "moet_obse": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        labels = {
            "moet_etap": "Etapa",
            "moet_ouri": "Ourives",
            "moet_dain": "Início",
            "moet_dafi": "Fim",
            "moet_peso": "Peso",
            "moet_situ": "Ativa ?",
            "moet_obse": "Observação",
        }


class ConsumoMateriaPrimaForm(forms.Form):
    consumido = forms.DecimalField(
        max_digits=16,
        decimal_places=4,
        required=True,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        label="Quantidade consumida",
    )
