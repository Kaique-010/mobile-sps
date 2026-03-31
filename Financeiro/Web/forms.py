from django import forms
from Financeiro.models import Orcamento
from Financeiro.models import OrcamentoItem
from CentrodeCustos.models import Centrodecustos 


class OrcamentoForm(forms.ModelForm):
    descricao = forms.CharField(
        label="Descrição",
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ex: Planejamento Financeiro 2026",
            }
        ),
    )

    ano = forms.IntegerField(
        label="Ano",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ex: 2026",
                "min": 2000,
            }
        ),
    )

    tipo = forms.ChoiceField(
        label="Tipo",
        choices=(
            ("A", "Anual"),
            ("M", "Mensal"),
        ),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    cenario = forms.ChoiceField(
        label="Cenário",
        choices=(
            ("R", "Realista"),
            ("P", "Pessimista"),
            ("O", "Otimista"),
        ),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    ativo = forms.BooleanField(
        label="Ativo",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = Orcamento
        fields = []
        # legado fica escondido, normalização fica aqui

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields["descricao"].initial = self.instance.orca_desc
            self.fields["ano"].initial = self.instance.orca_ano
            self.fields["tipo"].initial = self.instance.orca_tipo
            self.fields["cenario"].initial = self.instance.orca_cena
            self.fields["ativo"].initial = self.instance.orca_ativ

    def save(self, commit=True):
        instance = self.instance or Orcamento()
        instance.orca_desc = self.cleaned_data["descricao"]
        instance.orca_ano = self.cleaned_data["ano"]
        instance.orca_tipo = self.cleaned_data["tipo"]
        instance.orca_cena = self.cleaned_data["cenario"]
        instance.orca_ativ = self.cleaned_data["ativo"]

        if commit:
            instance.save()

        return instance


class OrcamentoItemForm(forms.ModelForm):
    centro_custo = forms.IntegerField(widget=forms.HiddenInput())
    centro_custo_display = forms.CharField(
        required=False,
        label="Centro de Custo",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Buscar centro de custo...",
                "autocomplete": "off",
            }
        ),
    )

    ano = forms.IntegerField(
        label="Ano",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": 2000,
            }
        ),
    )

    mes = forms.ChoiceField(
        label="Mês",
        choices=[(i, f"{i:02d}") for i in range(1, 13)],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    meses = forms.MultipleChoiceField(
        required=False,
        label="Meses",
        choices=[(i, f"{i:02d}") for i in range(1, 13)],
        widget=forms.CheckboxSelectMultiple(
            attrs={
                "class": "form-check-input",
                "role": "switch",
                "style": "width: 3em; height: 1.5em;",
            }
        ),
    )

    replicar_ano_todo = forms.BooleanField(
        required=False,
        label="Replicar para o ano todo",
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "role": "switch",
                "style": "width: 3em; height: 1.5em;",
            }
        ),
    )

    valor_previsto = forms.DecimalField(
        label="Valor Previsto",
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "step": "0.01",
                "placeholder": "0,00",
            }
        ),
    )

    observacao = forms.CharField(
        label="Observação",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Opcional",
            }
        ),
    )

    class Meta:
        model = OrcamentoItem
        fields = []

    def __init__(self, *args, **kwargs):
        db_alias = kwargs.pop("db_alias", "default")
        empresa_id = kwargs.pop("empresa_id", None)
        permitir_sintetico = kwargs.pop("permitir_sintetico", True)
        super().__init__(*args, **kwargs)
        self.db_alias = db_alias
        self.empresa_id = empresa_id
        self.permitir_sintetico = permitir_sintetico

        if self.instance and self.instance.pk:
            self.fields["centro_custo"].initial = self.instance.orci_cecu
            self.fields["ano"].initial = self.instance.orci_ano
            self.fields["mes"].initial = self.instance.orci_mes
            self.fields["valor_previsto"].initial = self.instance.orci_valo
            self.fields["observacao"].initial = self.instance.orci_obse
            centro = (
                Centrodecustos.objects.using(db_alias)
                .filter(cecu_empr=empresa_id, cecu_redu=self.instance.orci_cecu)
                .first()
                if empresa_id
                else None
            )
            if centro:
                self.fields["centro_custo_display"].initial = f"{centro.cecu_redu} - {centro.cecu_nome}"

    def clean_centro_custo(self):
        value = self.cleaned_data.get("centro_custo")
        if value in (None, ""):
            raise forms.ValidationError("Centro de custo é obrigatório.")
        try:
            cecu = int(value)
        except Exception:
            raise forms.ValidationError("Centro de custo inválido.")

        qs = Centrodecustos.objects.using(self.db_alias).filter(cecu_redu=cecu)
        if self.empresa_id:
            qs = qs.filter(cecu_empr=int(self.empresa_id))
        centro = qs.first()
        if not centro:
            raise forms.ValidationError("Centro de custo não encontrado.")
        if not self.permitir_sintetico and getattr(centro, "cecu_anal", None) != "A":
            raise forms.ValidationError("Somente centro de custo analítico pode receber lançamento.")
        return cecu

    def clean_meses(self):
        raw = self.cleaned_data.get("meses") or []
        out = []
        for v in raw:
            try:
                m = int(v)
            except Exception:
                continue
            if 1 <= m <= 12:
                out.append(m)
        return sorted(set(out))

    def save(self, commit=True):
        instance = self.instance or OrcamentoItem()
        instance.orci_cecu = int(self.cleaned_data["centro_custo"])
        instance.orci_ano = self.cleaned_data["ano"]
        instance.orci_mes = int(self.cleaned_data["mes"])
        instance.orci_valo = self.cleaned_data["valor_previsto"]
        instance.orci_obse = self.cleaned_data["observacao"]

        if commit:
            instance.save()

        return instance
