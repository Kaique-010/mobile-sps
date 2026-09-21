from django import forms

from Entidades.models import Entidades


class ImportarOFXForm(forms.Form):
    empresa = forms.ChoiceField(
        label="Empresa", widget=forms.Select(attrs={"class": "form-select"})
    )
    filial = forms.ChoiceField(
        label="Filial", widget=forms.Select(attrs={"class": "form-select"})
    )
    codigo_banco = forms.ChoiceField(
        label="Banco", widget=forms.Select(attrs={"class": "form-select"})
    )
    arquivo = forms.FileField(
        label="Arquivo OFX",
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".ofx"}),
    )

    def __init__(self, *args, **kwargs):
        self.contexto = kwargs.pop("contexto")
        super().__init__(*args, **kwargs)
        ctx = self.contexto
        self.fields["empresa"].choices = [(str(ctx.empresa), str(ctx.empresa))]
        self.fields["filial"].choices = [(str(ctx.filial), str(ctx.filial))]
        for campo in ("empresa", "filial"):
            self.fields[campo].initial = str(getattr(ctx, campo))
            self.fields[campo].help_text = (
                "Para selecionar outro contexto de empresa/filial, faça um novo login."
            )
            self.fields[campo].error_messages["invalid_choice"] = (
                "Selecione o contexto autorizado no login."
            )
        bancos = Entidades.objects.using(ctx.db_alias).filter(
            enti_empr=ctx.empresa, enti_tien="B"
        ).values_list("enti_clie", "enti_nome")
        self.fields["codigo_banco"].choices = [("", "Selecione um banco")] + [
            (str(codigo), "{} - {}".format(codigo, nome))
            for codigo, nome in bancos
        ]


class ConciliacaoFiltroForm(forms.Form):
    numero = forms.IntegerField(
        label="Número", required=False, min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    codigo_banco = forms.IntegerField(
        label="Código do banco", required=False, min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    data = forms.DateField(
        label="Data", required=False, input_formats=["%Y-%m-%d", "%d/%m/%Y"],
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}),
    )
