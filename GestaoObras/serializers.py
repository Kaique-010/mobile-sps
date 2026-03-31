from django.db.models import Max
from rest_framework import serializers

from ..models import Obra, ObraEtapa, ObraLancamentoFinanceiro, ObraMaterialMovimento, ObraProcesso


class CodigoSequencialMixin:
    codigo_field = None
    empresa_field = None
    filial_field = None

    def _next_codigo(self, model, empresa, filial):
        filtro = {
            self.empresa_field: empresa,
            self.filial_field: filial,
        }
        max_codi = model.objects.filter(**filtro).aggregate(max_codi=Max(self.codigo_field)).get("max_codi") or 0
        return max_codi + 1


class ObraSerializer(CodigoSequencialMixin, serializers.ModelSerializer):
    codigo_de_obra = serializers.IntegerField(source="obra_codi", required=False)
    obra_empresa = serializers.IntegerField(source="obra_empr")
    obra_filial = serializers.IntegerField(source="obra_fili")
    nome_da_obra = serializers.CharField(source="obra_nome")
    descricao_da_obra = serializers.CharField(source="obra_desc", required=False, allow_blank=True, allow_null=True)
    cliente_id = serializers.IntegerField(source="obra_clie_id")
    responsavel_id = serializers.IntegerField(source="obra_resp_id", required=False, allow_null=True)
    data_inicio = serializers.DateField(source="obra_dini")
    previsao_fim = serializers.DateField(source="obra_dpre", required=False, allow_null=True)
    data_fim = serializers.DateField(source="obra_dfim", required=False, allow_null=True)
    orcamento_total = serializers.DecimalField(source="obra_orca", max_digits=15, decimal_places=2)
    custo_total = serializers.DecimalField(source="obra_cust", max_digits=15, decimal_places=2, read_only=True)
    status_da_obra = serializers.CharField(source="obra_stat", required=False)
    obra_ativa = serializers.BooleanField(source="obra_ativ", required=False)

    codigo_field = "obra_codi"
    empresa_field = "obra_empr"
    filial_field = "obra_fili"

    class Meta:
        model = Obra
        fields = [
            "id", "codigo_de_obra", "obra_empresa", "obra_filial", "nome_da_obra", "descricao_da_obra",
            "cliente_id", "responsavel_id", "data_inicio", "previsao_fim", "data_fim",
            "orcamento_total", "custo_total", "status_da_obra", "obra_ativa",
        ]

    def create(self, validated_data):
        if not validated_data.get("obra_codi"):
            validated_data["obra_codi"] = self._next_codigo(Obra, validated_data["obra_empr"], validated_data["obra_fili"])
        return super().create(validated_data)


class ObraEtapaSerializer(CodigoSequencialMixin, serializers.ModelSerializer):
    codigo_da_etapa = serializers.IntegerField(source="etap_codi", required=False)
    etapa_empresa = serializers.IntegerField(source="etap_empr")
    etapa_filial = serializers.IntegerField(source="etap_fili")
    obra_id = serializers.IntegerField(source="etap_obra_id")
    nome_da_etapa = serializers.CharField(source="etap_nome")
    descricao_da_etapa = serializers.CharField(source="etap_desc", required=False, allow_blank=True, allow_null=True)
    ordem_da_etapa = serializers.IntegerField(source="etap_orde", required=False)
    data_inicio_prevista = serializers.DateField(source="etap_dinp", required=False, allow_null=True)
    data_fim_prevista = serializers.DateField(source="etap_dfip", required=False, allow_null=True)
    data_inicio_real = serializers.DateField(source="etap_dinr", required=False, allow_null=True)
    data_fim_real = serializers.DateField(source="etap_dfir", required=False, allow_null=True)
    situacao_da_etapa = serializers.CharField(source="etap_situ", required=False)
    percentual_conclusao = serializers.DecimalField(source="etap_perc", max_digits=5, decimal_places=2, required=False)

    codigo_field = "etap_codi"
    empresa_field = "etap_empr"
    filial_field = "etap_fili"

    class Meta:
        model = ObraEtapa
        fields = [
            "id", "codigo_da_etapa", "etapa_empresa", "etapa_filial", "obra_id", "nome_da_etapa",
            "descricao_da_etapa", "ordem_da_etapa", "data_inicio_prevista", "data_fim_prevista",
            "data_inicio_real", "data_fim_real", "situacao_da_etapa", "percentual_conclusao",
        ]

    def create(self, validated_data):
        if not validated_data.get("etap_codi"):
            validated_data["etap_codi"] = self._next_codigo(ObraEtapa, validated_data["etap_empr"], validated_data["etap_fili"])
        return super().create(validated_data)


class ObraMaterialMovimentoSerializer(CodigoSequencialMixin, serializers.ModelSerializer):
    codigo_do_movimento = serializers.IntegerField(source="movm_codi", required=False)
    movimento_empresa = serializers.IntegerField(source="movm_empr")
    movimento_filial = serializers.IntegerField(source="movm_fili")
    obra_id = serializers.IntegerField(source="movm_obra_id")
    etapa_id = serializers.IntegerField(source="movm_etap_id", required=False, allow_null=True)
    tipo_movimento = serializers.CharField(source="movm_tipo")
    produto_codigo = serializers.CharField(source="movm_prod")
    descricao_do_movimento = serializers.CharField(source="movm_desc")
    quantidade = serializers.DecimalField(source="movm_quan", max_digits=15, decimal_places=3)
    unidade = serializers.CharField(source="movm_unid", required=False)
    custo_unitario = serializers.DecimalField(source="movm_cuni", max_digits=15, decimal_places=6, required=False)
    data_movimento = serializers.DateField(source="movm_data")
    documento = serializers.CharField(source="movm_docu", required=False, allow_blank=True, allow_null=True)
    observacao = serializers.CharField(source="movm_obse", required=False, allow_blank=True, allow_null=True)

    codigo_field = "movm_codi"
    empresa_field = "movm_empr"
    filial_field = "movm_fili"

    class Meta:
        model = ObraMaterialMovimento
        fields = [
            "id", "codigo_do_movimento", "movimento_empresa", "movimento_filial", "obra_id", "etapa_id",
            "tipo_movimento", "produto_codigo", "descricao_do_movimento", "quantidade", "unidade",
            "custo_unitario", "data_movimento", "documento", "observacao",
        ]

    def create(self, validated_data):
        if not validated_data.get("movm_codi"):
            validated_data["movm_codi"] = self._next_codigo(
                ObraMaterialMovimento,
                validated_data["movm_empr"],
                validated_data["movm_fili"],
            )
        return super().create(validated_data)


class ObraLancamentoFinanceiroSerializer(CodigoSequencialMixin, serializers.ModelSerializer):
    codigo_do_lancamento = serializers.IntegerField(source="lfin_codi", required=False)
    lancamento_empresa = serializers.IntegerField(source="lfin_empr")
    lancamento_filial = serializers.IntegerField(source="lfin_fili")
    obra_id = serializers.IntegerField(source="lfin_obra_id")
    etapa_id = serializers.IntegerField(source="lfin_etap_id", required=False, allow_null=True)
    tipo_lancamento = serializers.CharField(source="lfin_tipo")
    categoria = serializers.CharField(source="lfin_cate")
    descricao = serializers.CharField(source="lfin_desc")
    valor = serializers.DecimalField(source="lfin_valo", max_digits=15, decimal_places=2)
    data_competencia = serializers.DateField(source="lfin_dcom")
    data_pagamento = serializers.DateField(source="lfin_dpag", required=False, allow_null=True)
    observacao = serializers.CharField(source="lfin_obse", required=False, allow_blank=True, allow_null=True)

    codigo_field = "lfin_codi"
    empresa_field = "lfin_empr"
    filial_field = "lfin_fili"

    class Meta:
        model = ObraLancamentoFinanceiro
        fields = [
            "id", "codigo_do_lancamento", "lancamento_empresa", "lancamento_filial", "obra_id", "etapa_id",
            "tipo_lancamento", "categoria", "descricao", "valor", "data_competencia", "data_pagamento",
            "observacao",
        ]

    def create(self, validated_data):
        if not validated_data.get("lfin_codi"):
            validated_data["lfin_codi"] = self._next_codigo(
                ObraLancamentoFinanceiro,
                validated_data["lfin_empr"],
                validated_data["lfin_fili"],
            )
        return super().create(validated_data)


class ObraProcessoSerializer(CodigoSequencialMixin, serializers.ModelSerializer):
    codigo_do_processo = serializers.IntegerField(source="proc_codi", required=False)
    processo_empresa = serializers.IntegerField(source="proc_empr")
    processo_filial = serializers.IntegerField(source="proc_fili")
    obra_id = serializers.IntegerField(source="proc_obra_id")
    etapa_id = serializers.IntegerField(source="proc_etap_id", required=False, allow_null=True)
    titulo_do_processo = serializers.CharField(source="proc_titu")
    descricao_do_processo = serializers.CharField(source="proc_desc", required=False, allow_blank=True, allow_null=True)
    responsavel_id = serializers.IntegerField(source="proc_resp_id", required=False, allow_null=True)
    data_limite = serializers.DateField(source="proc_dlim", required=False, allow_null=True)
    prioridade = serializers.CharField(source="proc_prio", required=False)
    status = serializers.CharField(source="proc_stat", required=False)

    codigo_field = "proc_codi"
    empresa_field = "proc_empr"
    filial_field = "proc_fili"

    class Meta:
        model = ObraProcesso
        fields = [
            "id", "codigo_do_processo", "processo_empresa", "processo_filial", "obra_id", "etapa_id",
            "titulo_do_processo", "descricao_do_processo", "responsavel_id", "data_limite", "prioridade", "status",
        ]

    def create(self, validated_data):
        if not validated_data.get("proc_codi"):
            validated_data["proc_codi"] = self._next_codigo(ObraProcesso, validated_data["proc_empr"], validated_data["proc_fili"])
        return super().create(validated_data)