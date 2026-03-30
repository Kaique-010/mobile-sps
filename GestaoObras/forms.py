from django import forms

from .models import Obra, ObraEtapa, ObraLancamentoFinanceiro, ObraMaterialMovimento, ObraProcesso


class ObraForm(forms.ModelForm):
    class Meta:
        model = Obra
        fields = "__all__"
        labels = {
            "obra_codi": "codigo_de_obra",
            "obra_empr": "obra_empresa",
            "obra_fili": "obra_filial",
            "obra_nome": "nome_da_obra",
            "obra_desc": "descricao_da_obra",
            "obra_dini": "data_inicio",
            "obra_dpre": "previsao_fim",
            "obra_dfim": "data_fim",
            "obra_orca": "orcamento_total",
            "obra_cust": "custo_total",
            "obra_stat": "status_da_obra",
            "obra_ativ": "obra_ativa",
        }


class ObraEtapaForm(forms.ModelForm):
    class Meta:
        model = ObraEtapa
        fields = "__all__"
        labels = {
            "etap_codi": "codigo_da_etapa",
            "etap_empr": "etapa_empresa",
            "etap_fili": "etapa_filial",
        }


class ObraMaterialMovimentoForm(forms.ModelForm):
    class Meta:
        model = ObraMaterialMovimento
        fields = "__all__"
        labels = {
            "movm_codi": "codigo_do_movimento",
            "movm_empr": "movimento_empresa",
            "movm_fili": "movimento_filial",
        }


class ObraLancamentoFinanceiroForm(forms.ModelForm):
    class Meta:
        model = ObraLancamentoFinanceiro
        fields = "__all__"
        labels = {
            "lfin_codi": "codigo_do_lancamento",
            "lfin_empr": "lancamento_empresa",
            "lfin_fili": "lancamento_filial",
        }


class ObraProcessoForm(forms.ModelForm):
    class Meta:
        model = ObraProcesso
        fields = "__all__"
        labels = {
            "proc_codi": "codigo_do_processo",
            "proc_empr": "processo_empresa",
            "proc_fili": "processo_filial",
        }
