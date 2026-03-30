from rest_framework import serializers

from GestaoObras.models import Obra, ObraEtapa, ObraLancamentoFinanceiro, ObraMaterialMovimento, ObraProcesso


class ObraSerializer(serializers.ModelSerializer):
    codigo_de_obra = serializers.IntegerField(source="obra_codi")
    obra_empresa = serializers.IntegerField(source="obra_empr")
    obra_filial = serializers.IntegerField(source="obra_fili")
    nome_da_obra = serializers.CharField(source="obra_nome")
    descricao_da_obra = serializers.CharField(source="obra_desc", required=False, allow_blank=True, allow_null=True)
    cliente_id = serializers.IntegerField(source="obra_clie")
    responsavel_id = serializers.IntegerField(source="obra_resp", required=False, allow_null=True)
    data_inicio = serializers.DateField(source="obra_dini")
    previsao_fim = serializers.DateField(source="obra_dpre", required=False, allow_null=True)
    data_fim = serializers.DateField(source="obra_dfim", required=False, allow_null=True)
    orcamento_total = serializers.DecimalField(source="obra_orca", max_digits=15, decimal_places=2)
    custo_total = serializers.DecimalField(source="obra_cust", max_digits=15, decimal_places=2, read_only=True)
    status_da_obra = serializers.CharField(source="obra_stat", required=False)
    obra_ativa = serializers.BooleanField(source="obra_ativ", required=False)

    class Meta:
        model = Obra
        fields = [
            "id",
            "codigo_de_obra",
            "obra_empresa",
            "obra_filial",
            "nome_da_obra",
            "descricao_da_obra",
            "cliente_id",
            "responsavel_id",
            "data_inicio",
            "previsao_fim",
            "data_fim",
            "orcamento_total",
            "custo_total",
            "status_da_obra",
            "obra_ativa",
        ]


class ObraEtapaSerializer(serializers.ModelSerializer):
    codigo_da_etapa = serializers.IntegerField(source="etap_codi")
    etapa_empresa = serializers.IntegerField(source="etap_empr")
    etapa_filial = serializers.IntegerField(source="etap_fili")
    obra_id = serializers.IntegerField(source="etap_obra_id")

    class Meta:
        model = ObraEtapa
        fields = [
            "id", "codigo_da_etapa", "etapa_empresa", "etapa_filial", "obra_id",
            "etap_nome", "etap_desc", "etap_orde", "etap_dinp", "etap_dfip",
            "etap_dinr", "etap_dfir", "etap_situ", "etap_perc",
        ]


class ObraMaterialMovimentoSerializer(serializers.ModelSerializer):
    codigo_do_movimento = serializers.IntegerField(source="movm_codi")
    movimento_empresa = serializers.IntegerField(source="movm_empr")
    movimento_filial = serializers.IntegerField(source="movm_fili")

    class Meta:
        model = ObraMaterialMovimento
        fields = [
            "id", "codigo_do_movimento", "movimento_empresa", "movimento_filial",
            "movm_obra", "movm_etap", "movm_tipo", "movm_prod", "movm_desc",
            "movm_quan", "movm_unid", "movm_cuni", "movm_data", "movm_docu", "movm_obse",
        ]


class ObraLancamentoFinanceiroSerializer(serializers.ModelSerializer):
    codigo_do_lancamento = serializers.IntegerField(source="lfin_codi")
    lancamento_empresa = serializers.IntegerField(source="lfin_empr")
    lancamento_filial = serializers.IntegerField(source="lfin_fili")

    class Meta:
        model = ObraLancamentoFinanceiro
        fields = [
            "id", "codigo_do_lancamento", "lancamento_empresa", "lancamento_filial",
            "lfin_obra", "lfin_etap", "lfin_tipo", "lfin_cate", "lfin_desc",
            "lfin_valo", "lfin_dcom", "lfin_dpag", "lfin_obse",
        ]


class ObraProcessoSerializer(serializers.ModelSerializer):
    codigo_do_processo = serializers.IntegerField(source="proc_codi")
    processo_empresa = serializers.IntegerField(source="proc_empr")
    processo_filial = serializers.IntegerField(source="proc_fili")

    class Meta:
        model = ObraProcesso
        fields = [
            "id", "codigo_do_processo", "processo_empresa", "processo_filial",
            "proc_obra", "proc_etap", "proc_titu", "proc_desc", "proc_resp",
            "proc_dlim", "proc_prio", "proc_stat",
        ]
