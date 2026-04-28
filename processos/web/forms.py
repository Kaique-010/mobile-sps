from django import forms

from processos.models import Processo, ProcessoChecklistResposta


class ProcessoTipoForm(forms.Form):
    nome = forms.CharField(max_length=120, label="Nome")
    codigo = forms.CharField(max_length=50, label="Código")
    ativo = forms.BooleanField(required=False, initial=True, label="Ativo")


class ChecklistModeloForm(forms.Form):
    processo_tipo_id = forms.IntegerField(label="Tipo de processo")
    nome = forms.CharField(max_length=120, label="Nome do modelo")
    versao = forms.IntegerField(min_value=1, initial=1, label="Versão")
    ativo = forms.BooleanField(required=False, initial=True, label="Ativo")


class ChecklistItemForm(forms.Form):
    checklist_modelo_id = forms.IntegerField(label="Modelo")
    ordem = forms.IntegerField(min_value=0, initial=0, label="Ordem")
    descricao = forms.CharField(max_length=255, label="Descrição")
    obrigatorio = forms.BooleanField(required=False, initial=True, label="Obrigatório")


class ProcessoForm(forms.ModelForm):
    class Meta:
        model = Processo
        fields = ["proc_tipo", "proc_desc"]
        labels = {"proc_tipo": "Tipo de processo", "proc_desc": "Descrição"}

    def __init__(self, *args, **kwargs):
        tipos = kwargs.pop("tipos", None)
        super().__init__(*args, **kwargs)
        if tipos is not None:
            self.fields["proc_tipo"].queryset = tipos


class ProcessoRespostaInlineForm(forms.Form):
    item_id = forms.IntegerField(widget=forms.HiddenInput)
    resposta = forms.ChoiceField(required=False, choices=ProcessoChecklistResposta.RESPOSTA_CHOICES)
    observacao = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
