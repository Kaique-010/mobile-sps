from rest_framework import serializers
from transportes.models import Cte

class CteEmissaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cte
        fields = [
            "id",
            "empresa",
            "filial",
            "modelo",
            "serie",
            "numero",
            "emissao",
            "hora",
            "remetente",
            "destinatario",
            "motorista",
            "veiculo",
            "tomador_servico",
            "tipo_servico",
            "tipo_cte",
            "forma_emissao",
            "tipo_frete",
            "status",
        ]
        read_only_fields = ['id', 'empresa', 'filial', 'numero', 'status']

    def create(self, validated_data):
        # Aqui, a criação inicial deve sempre garantir que o status seja RASCUNHO
        # e usar o RascunhoService, se houver lógica complexa.
        # Por enquanto, mantendo simples para o DRF.
        validated_data['status'] = 'RAS' # RASCUNHO
        return super().create(validated_data)

    def validate(self, data):
        # Validação básica de campos
        # Regras fiscais complexas vão para ValidacaoService
        return data
