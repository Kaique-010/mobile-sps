
from django import forms

from Entidades.models import Entidades


class ImportarOFXForm(forms.Form):
    empresa = forms.CharField(
        widget=forms.HiddenInput(),
    )
    filial = forms.CharField(
        widget=forms.HiddenInput(),
    )
    codigo_banco = forms.ChoiceField(
        label="Banco",
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )
    arquivo = forms.FileField(
        label="Arquivo OFX",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".ofx",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.contexto = kwargs.pop("contexto")
        super().__init__(*args, **kwargs)

        ctx = self.contexto

        self.fields["empresa"].initial = str(ctx.empresa)
        self.fields["filial"].initial = str(ctx.filial)

        bancos = Entidades.objects.using(
            ctx.db_alias
        ).filter(
            enti_empr=ctx.empresa,
            enti_tien="B",
        ).values_list(
            "enti_clie",
            "enti_nome",
        )

        self.fields["codigo_banco"].choices = [
            ("", "Selecione um banco"),
            *[
                (
                    str(codigo),
                    "{} - {}".format(codigo, nome),
                )
                for codigo, nome in bancos
            ],
        ]

    def clean_empresa(self):
        empresa = self.cleaned_data["empresa"]

        if empresa != str(self.contexto.empresa):
            raise forms.ValidationError(
                "Empresa incompatível com o contexto autenticado."
            )

        return self.contexto.empresa

    def clean_filial(self):
        filial = self.cleaned_data["filial"]

        if filial != str(self.contexto.filial):
            raise forms.ValidationError(
                "Filial incompatível com o contexto autenticado."
            )

        return self.contexto.filial


class ConciliacaoFiltroForm(forms.Form):
    numero = forms.IntegerField(
    required=False,
    min_value=1,
    widget=forms.NumberInput(attrs={
        "class": "form-control",
        "placeholder": "Número",
    }),
)

    codigo_banco = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Código do banco",
        }),
    )

    data = forms.DateField(
        required=False,
        input_formats=["%Y-%m-%d", "%d/%m/%Y"],
        widget=forms.DateInput(attrs={
            "class": "form-control",
            "type": "date",
        }),
    )