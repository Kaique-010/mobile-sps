from decimal import Decimal, InvalidOperation

from django import forms
from django.forms import formset_factory

from .models import Obra, ObraEtapa, ObraLancamentoFinanceiro, ObraMaterialMovimento, ObraProcesso


class BaseBootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.banco = kwargs.pop("banco", None)
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.HiddenInput):
                continue
            css_class = widget.attrs.get("class", "")
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                base_class = "form-select"
            elif isinstance(widget, forms.CheckboxInput):
                base_class = "form-check-input"
            else:
                base_class = "form-control"
            widget.attrs["class"] = f"{css_class} {base_class}".strip()
            if isinstance(widget, (forms.DateInput,)):
                try:
                    widget.input_type = "date"
                except Exception:
                    widget.attrs.setdefault("type", "date")


class ObraForm(BaseBootstrapModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "obra_codi" in self.fields:
            self.fields["obra_codi"].required = False
    cliente_busca = forms.CharField(required=False, widget=forms.TextInput(attrs={
        "placeholder": "Buscar cliente",
        "data-hidden-target": "id_obra_clie",
        "class": "autocomplete-entidades",
    }))
    responsavel_busca = forms.CharField(required=False, widget=forms.TextInput(attrs={
        "placeholder": "Buscar responsável",
        "data-hidden-target": "id_obra_resp",
        "class": "autocomplete-entidades",
    }))
    class Meta:
        model = Obra
        fields = "__all__"
        labels = {
            "obra_codi": "codigo_de_obra",
            "obra_empr": "obra_empresa",
            "obra_fili": "obra_filial",
            "obra_nome": "nome_da_obra",
            "obra_desc": "descricao_da_obra",
            "obra_clie": "cliente_id",
            "obra_resp": "responsavel_id",
            "obra_dini": "data_inicio",
            "obra_dpre": "previsao_fim",
            "obra_dfim": "data_fim",
            "obra_orca": "orcamento_total",
            "obra_cust": "custo_total",
            "obra_stat": "status_da_obra",
            "obra_ativ": "obra_ativa",
        }
        widgets = {
            "obra_codi": forms.HiddenInput(),
            "obra_stat": forms.Select(attrs={"class": "form-select"}),
            "obra_ativ": forms.CheckboxInput(),
            "obra_clie": forms.HiddenInput(attrs={"class": "form-control"}),
            "obra_resp": forms.HiddenInput(),
            "obra_dini": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "obra_dpre": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "obra_dfim": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "obra_orca": forms.NumberInput(attrs={"class": "form-control"}),
            "obra_cust": forms.NumberInput(attrs={"class": "form-control"}),
            
        }

    def clean(self):
        cleaned = super().clean()
        try:
            from GestaoObras.services.obras_service import ObrasService
            if not cleaned.get("obra_codi"):
                empr = cleaned.get("obra_empr")
                fili = cleaned.get("obra_fili")
                if self.banco and empr and fili:
                    cleaned["obra_codi"] = ObrasService.proximo_codigo_obra(self.banco, int(empr), int(fili))
        except Exception:
            pass
        return cleaned


class ObraEtapaForm(BaseBootstrapModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "etap_codi" in self.fields:
            self.fields["etap_codi"].required = False
            if getattr(self.instance, "pk", None):
                self.fields["etap_codi"].widget.attrs.setdefault("readonly", "readonly")
        if self.banco and "etap_obra" in self.fields:
            self.fields["etap_obra"].queryset = Obra.objects.using(self.banco).all()

    def clean(self):
        cleaned = super().clean()
        try:
            from GestaoObras.services.obras_service import ObrasService
            if not cleaned.get("etap_codi"):
                empr = cleaned.get("etap_empr")
                fili = cleaned.get("etap_fili")
                if self.banco and empr and fili:
                    cleaned["etap_codi"] = ObrasService.proximo_codigo_etapa(self.banco, int(empr), int(fili))
        except Exception:
            pass
        return cleaned

    class Meta:
        model = ObraEtapa
        fields = "__all__"
        labels = {
            "etap_codi": "codigo_da_etapa",
            "etap_empr": "etapa_empresa",
            "etap_fili": "etapa_filial",
        }
        widgets = {
            "etap_empr": forms.HiddenInput(),
            "etap_fili": forms.HiddenInput(),
            "etap_dinp": forms.DateInput(attrs={"type": "date"}),
            "etap_dfip": forms.DateInput(attrs={"type": "date"}),
            "etap_dinr": forms.DateInput(attrs={"type": "date"}),
            "etap_dfir": forms.DateInput(attrs={"type": "date"}),
        }


class ObraMaterialMovimentoForm(BaseBootstrapModelForm):
    gerar_financeiro = forms.BooleanField(
        required=False,
        label="Gerar Financeiro",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    movm_quan = forms.CharField(required=True, widget=forms.TextInput(attrs={"inputmode": "decimal"}))
    movm_cuni = forms.CharField(required=False, widget=forms.TextInput(attrs={"inputmode": "decimal"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.banco:
            if "movm_obra" in self.fields:
                self.fields["movm_obra"].queryset = Obra.objects.using(self.banco).all()
            if "movm_etap" in self.fields:
                self.fields["movm_etap"].queryset = ObraEtapa.objects.using(self.banco).all()

    def clean_movm_quan(self):
        val = (self.cleaned_data.get("movm_quan") or "").strip()
        if not val:
            raise forms.ValidationError("Informe a quantidade.")
        s = val.replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(".", "")
        s = s.replace(",", ".")
        try:
            return Decimal(s)
        except (InvalidOperation, ValueError):
            raise forms.ValidationError("Quantidade inválida.")

    def clean_movm_cuni(self):
        val = (self.cleaned_data.get("movm_cuni") or "").strip()
        if not val:
            return Decimal("0")
        s = val.replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(".", "")
        s = s.replace(",", ".")
        try:
            return Decimal(s)
        except (InvalidOperation, ValueError):
            raise forms.ValidationError("Custo unitário inválido.")

    class Meta:
        model = ObraMaterialMovimento
        fields = "__all__"
        labels = {
            "movm_codi": "codigo_do_movimento",
            "movm_empr": "movimento_empresa",
            "movm_fili": "movimento_filial",
        }
        widgets = {
            "movm_empr": forms.HiddenInput(),
            "movm_fili": forms.HiddenInput(),
            "movm_obra": forms.HiddenInput(),
            "movm_data": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "movm_tipo": forms.Select(attrs={"class": "form-select"}),
            "movm_etap": forms.Select(attrs={"class": "form-select"}),
            "movm_prod": forms.TextInput(attrs={"class": "form-control autocomplete-produtos", "autocomplete": "off"}),
            "movm_desc": forms.TextInput(attrs={"class": "form-control"}),
            "movm_unid": forms.TextInput(attrs={"class": "form-control"}),
            "movm_quan": forms.TextInput(attrs={"class": "form-control", "inputmode": "decimal"}),
            "movm_cuni": forms.TextInput(attrs={"class": "form-control", "inputmode": "decimal"}),
            "movm_docu": forms.TextInput(attrs={"class": "form-control"}),
            "movm_obse": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class ObraMaterialMovimentoCabecalhoForm(BaseBootstrapModelForm):
    gerar_financeiro = forms.BooleanField(
        required=False,
        label="Gerar Financeiro",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "movm_codi" in self.fields:
            self.fields["movm_codi"].required = False
            if getattr(self.instance, "pk", None):
                self.fields["movm_codi"].widget.attrs.setdefault("readonly", "readonly")
        if self.banco:
            if "movm_obra" in self.fields:
                self.fields["movm_obra"].queryset = Obra.objects.using(self.banco).all()
            if "movm_etap" in self.fields:
                self.fields["movm_etap"].queryset = ObraEtapa.objects.using(self.banco).all()

    def clean(self):
        cleaned = super().clean()
        try:
            from GestaoObras.services.obras_service import ObrasService
            if not cleaned.get("movm_codi"):
                empr = cleaned.get("movm_empr")
                fili = cleaned.get("movm_fili")
                if self.banco and empr and fili:
                    cleaned["movm_codi"] = ObrasService.proximo_codigo_movimento_material(self.banco, int(empr), int(fili))
        except Exception:
            pass
        return cleaned

    class Meta:
        model = ObraMaterialMovimento
        fields = ["movm_empr", "movm_fili", "movm_obra", "movm_codi", "movm_data", "movm_tipo", "movm_etap", "movm_docu", "movm_obse"]
        widgets = {
            "movm_empr": forms.HiddenInput(),
            "movm_fili": forms.HiddenInput(),
            "movm_obra": forms.HiddenInput(),
            "movm_data": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "movm_tipo": forms.Select(attrs={"class": "form-select"}),
            "movm_etap": forms.Select(attrs={"class": "form-select"}),
            "movm_docu": forms.TextInput(attrs={"class": "form-control"}),
            "movm_obse": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class ObraMaterialMovimentoItemForm(forms.Form):
    movm_prod = forms.CharField(
        required=False,
        label="Produto",
        widget=forms.TextInput(attrs={"class": "form-control produto-autocomplete", "autocomplete": "off"}),
    )
    movm_desc = forms.CharField(required=False, label="Descrição", widget=forms.TextInput(attrs={"class": "form-control item-desc"}))
    movm_unid = forms.CharField(required=False, label="Unid.", widget=forms.TextInput(attrs={"class": "form-control item-unid"}))
    movm_quan = forms.CharField(required=False, label="Quantidade", widget=forms.TextInput(attrs={"class": "form-control", "inputmode": "decimal"}))
    movm_cuni = forms.CharField(required=False, label="Custo Unit.", widget=forms.TextInput(attrs={"class": "form-control", "inputmode": "decimal"}))

    def clean(self):
        cleaned = super().clean()
        prod = (cleaned.get("movm_prod") or "").strip()
        if not prod:
            return cleaned
        quan_raw = (cleaned.get("movm_quan") or "").strip()
        if not quan_raw:
            self.add_error("movm_quan", "Informe a quantidade.")
        else:
            s = quan_raw.replace(" ", "")
            if "," in s and "." in s:
                s = s.replace(".", "")
            s = s.replace(",", ".")
            try:
                cleaned["movm_quan"] = Decimal(s)
            except (InvalidOperation, ValueError):
                self.add_error("movm_quan", "Quantidade inválida.")

        cuni_raw = (cleaned.get("movm_cuni") or "").strip()
        if cuni_raw:
            s = cuni_raw.replace(" ", "")
            if "," in s and "." in s:
                s = s.replace(".", "")
            s = s.replace(",", ".")
            try:
                cleaned["movm_cuni"] = Decimal(s)
            except (InvalidOperation, ValueError):
                self.add_error("movm_cuni", "Custo unitário inválido.")
        else:
            cleaned["movm_cuni"] = Decimal("0")

        if cleaned.get("movm_desc") in (None, ""):
            self.add_error("movm_desc", "Informe a descrição.")
        if cleaned.get("movm_unid") in (None, ""):
            self.add_error("movm_unid", "Informe a unidade.")
        return cleaned


ObraMaterialMovimentoItemFormSet = formset_factory(ObraMaterialMovimentoItemForm, extra=1, can_delete=False)


class ObraLancamentoFinanceiroForm(BaseBootstrapModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "lfin_codi" in self.fields:
            self.fields["lfin_codi"].required = False
            if getattr(self.instance, "pk", None):
                self.fields["lfin_codi"].widget.attrs.setdefault("readonly", "readonly")
        if self.banco:
            if "lfin_obra" in self.fields:
                self.fields["lfin_obra"].queryset = Obra.objects.using(self.banco).all()
            if "lfin_etap" in self.fields:
                self.fields["lfin_etap"].queryset = ObraEtapa.objects.using(self.banco).all()

    def clean(self):
        cleaned = super().clean()
        try:
            from GestaoObras.services.obras_service import ObrasService
            if not cleaned.get("lfin_codi"):
                empr = cleaned.get("lfin_empr")
                fili = cleaned.get("lfin_fili")
                if self.banco and empr and fili:
                    cleaned["lfin_codi"] = ObrasService.proximo_codigo_financeiro(self.banco, int(empr), int(fili))
        except Exception:
            pass
        return cleaned

    class Meta:
        model = ObraLancamentoFinanceiro
        fields = "__all__"
        labels = {
            "lfin_codi": "codigo_do_lancamento",
            "lfin_empr": "lancamento_empresa",
            "lfin_fili": "lancamento_filial",
        }
        widgets = {
            "lfin_empr": forms.HiddenInput(),
            "lfin_fili": forms.HiddenInput(),
            "lfin_dcom": forms.DateInput(attrs={"type": "date"}),
            "lfin_dpag": forms.DateInput(attrs={"type": "date"}),
        }


class ObraProcessoForm(BaseBootstrapModelForm):
    responsavel_busca = forms.CharField(required=False, widget=forms.TextInput(attrs={
        "placeholder": "Buscar responsável",
        "data-hidden-target": "id_proc_resp",
        "class": "autocomplete-entidades",
    }))
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.banco:
            if "proc_obra" in self.fields:
                self.fields["proc_obra"].queryset = Obra.objects.using(self.banco).all()
            if "proc_etap" in self.fields:
                self.fields["proc_etap"].queryset = ObraEtapa.objects.using(self.banco).all()

    class Meta:
        model = ObraProcesso
        fields = "__all__"
        labels = {
            "proc_codi": "codigo_do_processo",
            "proc_empr": "processo_empresa",
            "proc_fili": "processo_filial",
        }
        widgets = {
            "proc_empr": forms.HiddenInput(),
            "proc_fili": forms.HiddenInput(),
            "proc_resp": forms.HiddenInput(),
            "proc_dlim": forms.DateInput(attrs={"type": "date"}),
        }
