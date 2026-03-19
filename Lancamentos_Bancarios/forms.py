from django import forms

from .models import Lctobancario


class LancamentoBancarioForm(forms.ModelForm):
    banco_display = forms.CharField(
        required=False,
        label="Banco/Caixa",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Buscar banco/caixa...", "autocomplete": "off"}
        ),
    )
    centro_custo_display = forms.CharField(
        required=False,
        label="Centro de custo",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Buscar centro de custo...", "autocomplete": "off"}
        ),
    )
    entidade_display = forms.CharField(
        required=False,
        label="Entidade",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Buscar entidade...", "autocomplete": "off"}
        ),
    )

    class Meta:
        model = Lctobancario
        fields = [
            "laba_empr",
            "laba_fili",
            "laba_banc",
            "laba_data",
            "laba_cecu",
            "laba_valo",
            "laba_hist",
            "laba_enti",
        ]
        widgets = {
            "laba_empr": forms.NumberInput(attrs={"class": "form-control", "step": "1"}),
            "laba_fili": forms.NumberInput(attrs={"class": "form-control", "step": "1"}),
            "laba_banc": forms.HiddenInput(),
            "laba_data": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "laba_cecu": forms.HiddenInput(),
            "laba_valo": forms.NumberInput(attrs={"class": "form-control text-end", "step": "0.01", "placeholder": "0,00"}),
            "laba_hist": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "laba_enti": forms.HiddenInput(),
        }
        labels = {
            "laba_empr": "Empresa",
            "laba_fili": "Filial",
            "laba_banc": "Banco/Caixa",
            "laba_data": "Data",
            "laba_cecu": "Centro de custo",
            "laba_valo": "Valor",
            "laba_hist": "Histórico",
            "laba_enti": "Entidade",
        }

    def __init__(self, *args, **kwargs):
        self.db_alias = kwargs.pop("db_alias", None)
        self.empresa_id = kwargs.pop("empresa_id", None)
        super().__init__(*args, **kwargs)

        if "laba_banc" in self.fields:
            self.fields["laba_banc"].required = True

        instance = getattr(self, "instance", None)
        if instance and getattr(instance, "pk", None):
            self._set_display_initials_from_instance()

        if self.is_bound:
            self._sync_hidden_from_display()

        for name, field in self.fields.items():
            if self.is_bound and self.errors.get(name):
                css = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = (css + " is-invalid").strip()

    def _set_display_initials_from_instance(self):
        banco = self.db_alias or "default"
        try:
            from Entidades.models import Entidades
        except Exception:
            Entidades = None
        try:
            from CentrodeCustos.models import Centrodecustos
        except Exception:
            Centrodecustos = None

        if Entidades:
            if getattr(self.instance, "laba_banc", None):
                b = Entidades.objects.using(banco).filter(enti_clie=int(self.instance.laba_banc)).first()
                if b:
                    self.initial["banco_display"] = f"{b.enti_clie} - {b.enti_nome}"
            if getattr(self.instance, "laba_enti", None):
                e = Entidades.objects.using(banco).filter(enti_clie=int(self.instance.laba_enti)).first()
                if e:
                    self.initial["entidade_display"] = f"{e.enti_clie} - {e.enti_nome}"

        if Centrodecustos and getattr(self.instance, "laba_cecu", None):
            cc = Centrodecustos.objects.using(banco).filter(cecu_redu=int(self.instance.laba_cecu)).first()
            if cc:
                self.initial["centro_custo_display"] = f"{cc.cecu_redu} - {cc.cecu_nome}"

    def _sync_hidden_from_display(self):
        for hidden_name, display_name in (
            ("laba_banc", "banco_display"),
            ("laba_cecu", "centro_custo_display"),
            ("laba_enti", "entidade_display"),
        ):
            raw_hidden = (self.data.get(hidden_name) or "").strip()
            raw_display = (self.data.get(display_name) or "").strip()
            if raw_hidden:
                continue
            if not raw_display:
                continue
            head = raw_display.split(" - ", 1)[0].strip()
            if head.isdigit():
                if hasattr(self.data, "_mutable"):
                    was_mutable = self.data._mutable
                    self.data._mutable = True
                    self.data[hidden_name] = head
                    self.data._mutable = was_mutable
                else:
                    try:
                        self.data[hidden_name] = head
                    except Exception:
                        pass
