from django import forms

from transportes.models import Mdfe, MdfeDocumento, Mdfeantt, Mdfecontratante, Mdfeseguro
from core.utils import get_licenca_db_config
from series.service import SeriesService
from series.models import Series


class MdfeForm(forms.ModelForm):
    class Meta:
        model = Mdfe
        fields = [
            "mdf_emis",
            "mdf_nume",
            "mdf_seri",
            "mdf_esta_orig",
            "mdf_esta_dest",
            "mdf_cida_carr",
            "mdf_nome_carr",
            "mdf_tipo_emit",
            "mdf_tipo_tran",
            "mdf_pred_carg",
            "mdf_pred_xprod",
            "mdf_pred_ncm",
            "mdf_pred_ean",
            "mdf_tran",
            "mdf_moto",
            "mdf_veic",
        ]
        widgets = {
            "mdf_emis": forms.DateInput(attrs={"type": "date"}),
            "mdf_esta_orig": forms.Select(attrs={"class": "form-select"}),
            "mdf_esta_dest": forms.Select(attrs={"class": "form-select"}),
            "mdf_tran": forms.HiddenInput(attrs={"class": "form-control"}),
            "mdf_moto": forms.HiddenInput(attrs={"class": "form-control"}),
            "mdf_veic": forms.HiddenInput(attrs={"class": "form-control"}),
            "mdf_nome_carr": forms.HiddenInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        self.fields["mdf_seri"].required = False
        self.fields["mdf_nume"].required = False

        ufs = [
            ("AC", "AC"),
            ("AL", "AL"),
            ("AP", "AP"),
            ("AM", "AM"),
            ("BA", "BA"),
            ("CE", "CE"),
            ("DF", "DF"),
            ("ES", "ES"),
            ("GO", "GO"),
            ("MA", "MA"),
            ("MT", "MT"),
            ("MS", "MS"),
            ("MG", "MG"),
            ("PA", "PA"),
            ("PB", "PB"),
            ("PR", "PR"),
            ("PE", "PE"),
            ("PI", "PI"),
            ("RJ", "RJ"),
            ("RN", "RN"),
            ("RS", "RS"),
            ("RO", "RO"),
            ("RR", "RR"),
            ("SC", "SC"),
            ("SP", "SP"),
            ("SE", "SE"),
            ("TO", "TO"),
        ]
        self.fields["mdf_esta_orig"].widget = forms.Select(choices=[("", "---------")] + ufs)
        self.fields["mdf_esta_dest"].widget = forms.Select(choices=[("", "---------")] + ufs)

        if request is not None:
            banco = get_licenca_db_config(request) or "default"
            empresa_id = request.session.get("empresa_id")
            filial_id = request.session.get("filial_id") or 1
            if empresa_id:
                qs_series = SeriesService.get_series_by_type(empresa_id, filial_id, "MD", using=banco)
                if not qs_series.exists():
                    qs_series = SeriesService.get_series_by_type(empresa_id, filial_id, "MDFE", using=banco)
                if not qs_series.exists():
                    qs_series = Series.objects.using(banco).filter(seri_empr=empresa_id, seri_nome="MD")
                if not qs_series.exists():
                    qs_series = Series.objects.using(banco).filter(seri_empr=empresa_id, seri_nome="MDFE")
                qs_series = qs_series.order_by("seri_codi").values_list("seri_codi", flat=True)
                opcoes = []
                for codi in list(qs_series):
                    raw = str(codi or "").strip()
                    if not raw:
                        continue
                    if raw.isdigit():
                        opcoes.append((int(raw), raw.zfill(3)))
                if opcoes:
                    self.fields["mdf_seri"].widget = forms.Select()
                    self.fields["mdf_seri"].choices = opcoes
                    if not (self.instance and getattr(self.instance, "mdf_seri", None)):
                        self.initial.setdefault("mdf_seri", opcoes[0][0])

        if not (self.instance and getattr(self.instance, "mdf_id", None)):
            self.fields["mdf_nume"].widget.attrs.setdefault("readonly", "readonly")
                
        for name, field in self.fields.items():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)


class MdfeDocumentoForm(forms.ModelForm):
    class Meta:
        model = MdfeDocumento
        fields = ["tipo_doc", "chave", "cmun_descarga", "xmun_descarga"]
        widgets = {
            "tipo_doc": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)


class MdfeAnttForm(forms.ModelForm):
    class Meta:
        model = Mdfeantt
        fields = ["mdfe_antt_rntrc", "mdfe_antt_ciot", "mdfe_antt_cpf", "mdfe_antt_cnpj"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)


class MdfeContratanteForm(forms.ModelForm):
    class Meta:
        model = Mdfecontratante
        fields = ["mdfe_cont_cont", "mdfe_cont_cnpj_cpf"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)


class MdfeSeguroForm(forms.ModelForm):
    class Meta:
        model = Mdfeseguro
        fields = [
            "mdfe_segu_resp",
            "mdfe_segu_cnpj_resp",
            "mdfe_segu_cpf_resp",
            "mdfe_segu_nome_segu",
            "mdfe_segu_cnpj_segu",
            "mdfe_segu_apol",
            "mdfe_segu_aver",
        ]
        widgets = {
            "mdfe_segu_resp": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)
