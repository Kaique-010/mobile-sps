from django import forms

from Produtos.models import Produtos


class OrdemProducaoForm(forms.Form):
    op_data = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Data",
    )
    op_prod = forms.ModelChoiceField(
        queryset=Produtos.objects.none(),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Produto",
    )
    op_vers = forms.IntegerField(
        required=True,
        min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "inputmode": "numeric"}),
        label="Versão",
    )
    op_quan = forms.DecimalField(
        required=True,
        min_value=0,
        decimal_places=4,
        max_digits=15,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.0001", "inputmode": "decimal"}),
        label="Quantidade",
    )
    op_lote = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="Lote",
    )
    auto_lote = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Gerar lote automaticamente",
    )

    def __init__(self, *args, **kwargs):
        database = kwargs.pop("database", None)
        empresa_id = kwargs.pop("empresa_id", None)
        super().__init__(*args, **kwargs)

        qs = Produtos.objects.none()
        if database:
            qs = Produtos.objects.using(database)
            if empresa_id is not None:
                qs = qs.filter(prod_empr=str(empresa_id))
        self.fields["op_prod"].queryset = qs.order_by("prod_nome")
        self.fields["op_prod"].label_from_instance = lambda obj: f"{obj.prod_codi} - {obj.prod_nome}"


class FormulaProdutoCreateForm(forms.Form):
    form_prod = forms.ModelChoiceField(
        queryset=Produtos.objects.none(),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Produto",
    )
    form_vers = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "inputmode": "numeric"}),
        label="Versão",
    )
    form_ativ = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Ativa",
    )
    auto_vers = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Gerar versão sequencial",
    )

    def __init__(self, *args, **kwargs):
        database = kwargs.pop("database", None)
        empresa_id = kwargs.pop("empresa_id", None)
        super().__init__(*args, **kwargs)

        qs = Produtos.objects.none()
        if database:
            qs = Produtos.objects.using(database)
            if empresa_id is not None:
                qs = qs.filter(prod_empr=str(empresa_id))
        self.fields["form_prod"].queryset = qs.order_by("prod_nome")
        self.fields["form_prod"].label_from_instance = lambda obj: f"{obj.prod_codi} - {obj.prod_nome}"

    def clean(self):
        cleaned = super().clean()
        auto_vers = bool(cleaned.get("auto_vers"))
        vers = cleaned.get("form_vers")
        if not auto_vers and (vers is None or str(vers).strip() == ""):
            self.add_error("form_vers", "Este campo é obrigatório.")
        return cleaned


class FormulaItemAddForm(forms.Form):
    form_insu = forms.ModelChoiceField(
        queryset=Produtos.objects.none(),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Insumo",
    )
    form_qtde = forms.DecimalField(
        required=True,
        min_value=0,
        decimal_places=4,
        max_digits=15,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.0001", "inputmode": "decimal"}),
        label="Quantidade",
    )
    form_perd_perc = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=5,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "inputmode": "decimal"}),
        label="Perda (%)",
    )

    def __init__(self, *args, **kwargs):
        database = kwargs.pop("database", None)
        empresa_id = kwargs.pop("empresa_id", None)
        super().__init__(*args, **kwargs)

        qs = Produtos.objects.none()
        if database:
            qs = Produtos.objects.using(database)
            if empresa_id is not None:
                qs = qs.filter(prod_empr=str(empresa_id))
        self.fields["form_insu"].queryset = qs.order_by("prod_nome")
        self.fields["form_insu"].label_from_instance = lambda obj: f"{obj.prod_codi} - {obj.prod_nome}"


class FormulaSaidaAddForm(forms.Form):
    said_prod = forms.ModelChoiceField(
        queryset=Produtos.objects.none(),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Produto",
    )
    said_quan = forms.DecimalField(
        required=True,
        min_value=0,
        decimal_places=4,
        max_digits=15,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.0001", "inputmode": "decimal"}),
        label="Quantidade",
    )
    said_perc_cust = forms.DecimalField(
        required=True,
        min_value=0,
        decimal_places=2,
        max_digits=5,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "inputmode": "decimal"}),
        label="Custo (%)",
    )
    said_principal = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Principal",
    )

    def __init__(self, *args, **kwargs):
        database = kwargs.pop("database", None)
        empresa_id = kwargs.pop("empresa_id", None)
        super().__init__(*args, **kwargs)

        qs = Produtos.objects.none()
        if database:
            qs = Produtos.objects.using(database)
            if empresa_id is not None:
                qs = qs.filter(prod_empr=str(empresa_id))
        self.fields["said_prod"].queryset = qs.order_by("prod_nome")
        self.fields["said_prod"].label_from_instance = lambda obj: f"{obj.prod_codi} - {obj.prod_nome}"


class OrdemProducaoAutoFieldsMixin(forms.Form):
    auto_lote = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Gerar lote automaticamente",
    )


class OrdemProducaoEditForm(forms.Form):
    op_data = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Data",
    )
    op_quan = forms.DecimalField(
        required=True,
        min_value=0,
        decimal_places=4,
        max_digits=15,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.0001", "inputmode": "decimal"}),
        label="Quantidade",
    )
    op_lote = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="Lote",
    )
    auto_lote = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Gerar lote automaticamente",
    )
    preco_vista = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=15,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "inputmode": "decimal"}),
        label="Preço à vista",
    )
    preco_prazo = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=15,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "inputmode": "decimal"}),
        label="Preço a prazo",
    )
