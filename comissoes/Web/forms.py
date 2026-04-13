from typing import Optional

from django import forms
from comissoes.models import LancamentoComissao, PagamentoComissao, RegraComissao


def _parse_beneficiario(valor):
    v = str(valor or "").strip()
    if not v:
        return None
    head = v.split("-", 1)[0].strip()
    if head.isdigit():
        return int(head)
    if v.isdigit():
        return int(v)
    return None


def _parse_centro_custo(valor):
    v = str(valor or "").strip()
    if not v:
        return None
    head = v.split("-", 1)[0].strip()
    if head.isdigit():
        return int(head)
    if v.isdigit():
        return int(v)
    return None


def _resolver_centro_custo_display(*, request, cecu_id: Optional[int]):
    if not request or not cecu_id:
        return None
    try:
        from core.utils import get_licenca_db_config
        from CentrodeCustos.models import Centrodecustos
    except Exception:
        return None

    banco = get_licenca_db_config(request) or "default"
    cc = Centrodecustos.objects.using(banco).filter(cecu_redu=int(cecu_id)).first()
    if not cc:
        return None
    return f"{cc.cecu_redu} - {cc.cecu_nome}"


class RegraComissaoForm(forms.ModelForm):
    beneficiario_busca = forms.CharField(required=True)
    centro_custo_display = forms.CharField(required=False)

    class Meta:
        model = RegraComissao
        fields = [
            "regc_bene",
            "regc_perc",
            "regc_ativ",
            "regc_data_ini",
            "regc_data_fim",
            "regc_cecu",
        ]
        widgets = {
            "regc_data_ini": forms.DateInput(attrs={"type": "date"}),
            "regc_data_fim": forms.DateInput(attrs={"type": "date"}),
            "regc_perc": forms.NumberInput(attrs={"step": "0.01"}),
            "regc_cecu": forms.NumberInput(attrs={"step": "1"}),
        }
        labels = {
            "regc_bene": RegraComissao._meta.get_field("regc_bene").verbose_name,
            "regc_perc": RegraComissao._meta.get_field("regc_perc").verbose_name,
            "regc_ativ": RegraComissao._meta.get_field("regc_ativ").verbose_name,
            "regc_data_ini": RegraComissao._meta.get_field("regc_data_ini").verbose_name,
            "regc_data_fim": RegraComissao._meta.get_field("regc_data_fim").verbose_name,
            "regc_cecu": RegraComissao._meta.get_field("regc_cecu").verbose_name,
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        self.fields["beneficiario_busca"].label = self.fields["regc_bene"].label
        self.fields["beneficiario_busca"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Digite código ou nome...",
                "autocomplete": "off",
                "id": "beneficiario_busca",
                "list": "beneficiarios_options",
            }
        )

        self.fields["regc_bene"].widget = forms.HiddenInput()
        self.fields["regc_bene"].required = False
        self.fields["regc_cecu"].widget = forms.HiddenInput()
        self.fields["regc_cecu"].required = False
        self.fields["centro_custo_display"].label = self.fields["regc_cecu"].label
        self.fields["centro_custo_display"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Buscar centro de custo...",
                "autocomplete": "off",
            }
        )

        self.fields["regc_perc"].widget.attrs.update({"class": "form-control", "placeholder": "Percentual"})
        self.fields["regc_ativ"].widget.attrs.update({"class": "form-check-input"})
        self.fields["regc_data_ini"].widget.attrs.update({"class": "form-control", "type": "date"})
        self.fields["regc_data_fim"].widget.attrs.update({"class": "form-control", "type": "date"})

        if self.instance and getattr(self.instance, "regc_bene", None):
            self.fields["beneficiario_busca"].initial = str(self.instance.regc_bene)
        if self.instance and getattr(self.instance, "regc_cecu", None):
            display = _resolver_centro_custo_display(request=self.request, cecu_id=self.instance.regc_cecu)
            if display:
                self.fields["centro_custo_display"].initial = display

        if self.is_bound:
            raw_hidden = str(self.data.get("regc_cecu") or "").strip()
            raw_display = str(self.data.get("centro_custo_display") or "").strip()
            if not raw_hidden and raw_display:
                parsed = _parse_centro_custo(raw_display)
                if parsed is not None:
                    if hasattr(self.data, "_mutable"):
                        was_mutable = self.data._mutable
                        self.data._mutable = True
                        self.data["regc_cecu"] = str(parsed)
                        self.data._mutable = was_mutable
                    else:
                        try:
                            self.data["regc_cecu"] = str(parsed)
                        except Exception:
                            pass

    def clean(self):
        cleaned = super().clean()
        bene = _parse_beneficiario(cleaned.get("beneficiario_busca"))
        if bene is None:
            bene = cleaned.get("regc_bene")
        if bene is None:
            raise forms.ValidationError("Informe o beneficiário.")
        cleaned["regc_bene"] = int(bene)

        cecu = cleaned.get("regc_cecu")
        if cecu in ("", None):
            cecu = _parse_centro_custo(cleaned.get("centro_custo_display"))
        cleaned["regc_cecu"] = int(cecu) if cecu not in ("", None) else 0
        return cleaned


class RegraFiltroForm(forms.Form):
    beneficiario_busca = forms.CharField(required=False, label=RegraComissao._meta.get_field("regc_bene").verbose_name)
    ativas = forms.ChoiceField(required=False, choices=[("", "Todas"), ("1", "Ativas"), ("0", "Inativas")], label="Ativo")

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        self.fields["beneficiario_busca"].widget.attrs.update(
            {"class": "form-control", "id": "beneficiario_busca", "list": "beneficiarios_options", "autocomplete": "off"}
        )
        self.fields["ativas"].widget.attrs.update({"class": "form-select"})

    def beneficiario_id(self):
        return _parse_beneficiario(self.cleaned_data.get("beneficiario_busca"))

    def ativas_bool(self):
        raw = str(self.cleaned_data.get("ativas") or "").strip()
        if raw == "1":
            return True
        if raw == "0":
            return False
        return None


class LancamentoFiltroForm(forms.Form):
    centro_custo_display = forms.CharField(required=False, label=LancamentoComissao._meta.get_field("lcom_cecu").verbose_name)
    beneficiario_busca = forms.CharField(required=False, label=LancamentoComissao._meta.get_field("lcom_bene").verbose_name)
    tipo_origem = forms.ChoiceField(
        required=False,
        choices=[("", "Todos")] + list(LancamentoComissao.TIPO_ORIGEM_CHOICES),
        label=LancamentoComissao._meta.get_field("lcom_tipo_origem").verbose_name,
    )
    status = forms.ChoiceField(
        required=False,
        choices=[("", "Todos")] + [(str(x[0]), x[1]) for x in LancamentoComissao.STATUS_CHOICES],
        label="Status",
    )
    documento = forms.CharField(required=False, label=LancamentoComissao._meta.get_field("lcom_docu").verbose_name)
    data_ini = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="Data Inicial")
    data_fim = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="Data Final")
    valor_min = forms.DecimalField(required=False, decimal_places=2, max_digits=14, label="Valor (min)")
    valor_max = forms.DecimalField(required=False, decimal_places=2, max_digits=14, label="Valor (max)")
    cento_custo = forms.IntegerField(required=False, label=LancamentoComissao._meta.get_field("lcom_cecu").verbose_name)    

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "form-check-input"})
            elif isinstance(field.widget, (forms.Select,)):
                field.widget.attrs.update({"class": "form-select"})
            else:
                field.widget.attrs.update({"class": "form-control"})
        self.fields["beneficiario_busca"].widget.attrs.update(
            {"id": "beneficiario_busca", "list": "beneficiarios_options", "autocomplete": "off"}
        )
        self.fields["cento_custo"].widget = forms.HiddenInput()
        self.fields["centro_custo_display"].widget.attrs.update({"autocomplete": "off"})

        if self.is_bound:
            raw_hidden = str(self.data.get("cento_custo") or "").strip()
            raw_display = str(self.data.get("centro_custo_display") or "").strip()
            if not raw_hidden and raw_display:
                parsed = _parse_centro_custo(raw_display)
                if parsed is not None:
                    if hasattr(self.data, "_mutable"):
                        was_mutable = self.data._mutable
                        self.data._mutable = True
                        self.data["cento_custo"] = str(parsed)
                        self.data._mutable = was_mutable
                    else:
                        try:
                            self.data["cento_custo"] = str(parsed)
                        except Exception:
                            pass

            if raw_hidden and not raw_display:
                display = _resolver_centro_custo_display(request=self.request, cecu_id=int(raw_hidden))
                if display:
                    if hasattr(self.data, "_mutable"):
                        was_mutable = self.data._mutable
                        self.data._mutable = True
                        self.data["centro_custo_display"] = display
                        self.data._mutable = was_mutable

    def beneficiario_id(self):
        return _parse_beneficiario(self.cleaned_data.get("beneficiario_busca"))

    def centro_custo_id(self):
        cecu = self.cleaned_data.get("cento_custo")
        if cecu in ("", None):
            return None
        try:
            return int(cecu)
        except Exception:
            return None


class PagamentoFiltroForm(forms.Form):
    centro_custo_display = forms.CharField(required=False, label=PagamentoComissao._meta.get_field("pagc_cecu").verbose_name)
    beneficiario_busca = forms.CharField(required=False, label=PagamentoComissao._meta.get_field("pagc_bene").verbose_name)
    data_ini = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="Data Inicial")
    data_fim = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="Data Final")
    valor_min = forms.DecimalField(required=False, decimal_places=2, max_digits=14, label="Valor (min)")
    valor_max = forms.DecimalField(required=False, decimal_places=2, max_digits=14, label="Valor (max)")
    cento_custo = forms.IntegerField(required=False, label=PagamentoComissao._meta.get_field("pagc_cecu").verbose_name)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})
        self.fields["beneficiario_busca"].widget.attrs.update(
            {"id": "beneficiario_busca", "list": "beneficiarios_options", "autocomplete": "off"}
        )
        self.fields["cento_custo"].widget = forms.HiddenInput()
        self.fields["centro_custo_display"].widget.attrs.update({"autocomplete": "off"})

        if self.is_bound:
            raw_hidden = str(self.data.get("cento_custo") or "").strip()
            raw_display = str(self.data.get("centro_custo_display") or "").strip()
            if not raw_hidden and raw_display:
                parsed = _parse_centro_custo(raw_display)
                if parsed is not None:
                    if hasattr(self.data, "_mutable"):
                        was_mutable = self.data._mutable
                        self.data._mutable = True
                        self.data["cento_custo"] = str(parsed)
                        self.data._mutable = was_mutable
                    else:
                        try:
                            self.data["cento_custo"] = str(parsed)
                        except Exception:
                            pass

            if raw_hidden and not raw_display:
                display = _resolver_centro_custo_display(request=self.request, cecu_id=int(raw_hidden))
                if display:
                    if hasattr(self.data, "_mutable"):
                        was_mutable = self.data._mutable
                        self.data._mutable = True
                        self.data["centro_custo_display"] = display
                        self.data._mutable = was_mutable

    def beneficiario_id(self):
        return _parse_beneficiario(self.cleaned_data.get("beneficiario_busca"))

    def centro_custo_id(self):
        cecu = self.cleaned_data.get("cento_custo")
        if cecu in ("", None):
            return None
        try:
            return int(cecu)
        except Exception:
            return None


class PagamentoCriarForm(forms.Form):
    centro_custo_display = forms.CharField(required=False, label=PagamentoComissao._meta.get_field("pagc_cecu").verbose_name)
    beneficiario_busca = forms.CharField(required=True, label=PagamentoComissao._meta.get_field("pagc_bene").verbose_name)
    data = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={"type": "date"}),
        label=PagamentoComissao._meta.get_field("pagc_data").verbose_name,
    )
    observacao = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label=PagamentoComissao._meta.get_field("pagc_obse").verbose_name,
    )
    cento_custo = forms.IntegerField(required=False, label=PagamentoComissao._meta.get_field("pagc_cecu").verbose_name)



    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": "form-control"})
            else:
                field.widget.attrs.update({"class": "form-control"})
        self.fields["beneficiario_busca"].widget.attrs.update(
            {"id": "beneficiario_busca", "list": "beneficiarios_options", "autocomplete": "off"}
        )
        self.fields["cento_custo"].widget = forms.HiddenInput()
        self.fields["centro_custo_display"].widget.attrs.update({"autocomplete": "off"})

        if self.is_bound:
            raw_hidden = str(self.data.get("cento_custo") or "").strip()
            raw_display = str(self.data.get("centro_custo_display") or "").strip()
            if not raw_hidden and raw_display:
                parsed = _parse_centro_custo(raw_display)
                if parsed is not None:
                    if hasattr(self.data, "_mutable"):
                        was_mutable = self.data._mutable
                        self.data._mutable = True
                        self.data["cento_custo"] = str(parsed)
                        self.data._mutable = was_mutable
                    else:
                        try:
                            self.data["cento_custo"] = str(parsed)
                        except Exception:
                            pass

            if raw_hidden and not raw_display:
                display = _resolver_centro_custo_display(request=self.request, cecu_id=int(raw_hidden))
                if display:
                    if hasattr(self.data, "_mutable"):
                        was_mutable = self.data._mutable
                        self.data._mutable = True
                        self.data["centro_custo_display"] = display
                        self.data._mutable = was_mutable

    def beneficiario_id(self):
        bene = _parse_beneficiario(self.cleaned_data.get("beneficiario_busca"))
        if bene is None:
            raise forms.ValidationError("Informe o beneficiário.")
        return bene

    def centro_custo_id(self):
        cecu = self.cleaned_data.get("cento_custo")
        if cecu in ("", None):
            return None
        try:
            return int(cecu)
        except Exception:
            return None
