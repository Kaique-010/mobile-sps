from rest_framework import serializers

from processos.models import (
    ChecklistItem,
    ChecklistModelo,
    Processo,
    ProcessoChecklistResposta,
    ProcessoTipo,
)


class ProcessoTipoSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(source="prot_nome")
    codigo = serializers.CharField(source="prot_codi")
    ativo = serializers.BooleanField(source="prot_ativ", required=False)

    class Meta:
        model = ProcessoTipo
        fields = ["id", "nome", "codigo", "ativo"]


class ChecklistModeloSerializer(serializers.ModelSerializer):
    processo_tipo_id = serializers.IntegerField(source="chmo_proc_tipo_id")
    nome = serializers.CharField(source="chmo_nome")
    versao = serializers.IntegerField(source="chmo_vers")
    ativo = serializers.BooleanField(source="chmo_ativ", required=False)

    class Meta:
        model = ChecklistModelo
        fields = ["id", "processo_tipo_id", "nome", "versao", "ativo"]


class ChecklistItemSerializer(serializers.ModelSerializer):
    checklist_modelo_id = serializers.IntegerField(source="chit_mode_id")
    ordem = serializers.IntegerField(source="chit_orde")
    descricao = serializers.CharField(source="chit_desc")
    obrigatorio = serializers.BooleanField(source="chit_obri")

    class Meta:
        model = ChecklistItem
        fields = ["id", "checklist_modelo_id", "ordem", "descricao", "obrigatorio"]


class ProcessoChecklistRespostaSerializer(serializers.ModelSerializer):
    item_id = serializers.IntegerField(source="pchr_item_id")
    resposta = serializers.CharField(source="pchr_resp", allow_blank=True, allow_null=True, required=False)
    observacao = serializers.CharField(source="pchr_obse", allow_blank=True, allow_null=True, required=False)

    class Meta:
        model = ProcessoChecklistResposta
        fields = ["id", "item_id", "resposta", "observacao", "pchr_vali"]


class ProcessoSerializer(serializers.ModelSerializer):
    tipo_id = serializers.IntegerField(source="proc_tipo_id")
    descricao = serializers.CharField(source="proc_desc")
    status = serializers.CharField(source="proc_stat", read_only=True)
    respostas = ProcessoChecklistRespostaSerializer(many=True, read_only=True)

    class Meta:
        model = Processo
        fields = ["id", "tipo_id", "descricao", "status", "respostas", "proc_data_aber", "proc_data_fech"]
