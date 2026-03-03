from rest_framework import serializers
from ..models import OrdensEletro

class OrdensEletroSerializer(serializers.ModelSerializer):
    total_os = serializers.DecimalField(source='total_orde', max_digits=12, decimal_places=2, read_only=True)
    status_ordem = serializers.CharField(source='status_orde', max_length=50, read_only=True)
    
    # Redefinir campos que podem vir vazios do banco legado para evitar erro de conversão int('')
    pedido_compra = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    nf_entrada = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # Campos de data blindados
    data_abertura = serializers.SerializerMethodField()
    data_fim = serializers.SerializerMethodField()
    ultima_alteracao = serializers.SerializerMethodField()

    class Meta:
        model = OrdensEletro
        fields = [
            'empresa', 'filial', 'ordem_de_servico', 'cliente', 'nome_cliente',
            'data_abertura', 'data_fim', 'setor', 'setor_nome', 'pecas', 'servicos',
            'total_orde', 'total_os', 'status_orde', 'status_ordem', 'responsavel', 
            'nome_responsavel', 'potencia', 'ultima_alteracao', 'pedido_compra', 'nf_entrada'
        ]

    def get_data_abertura(self, obj):
        # Tenta pegar a versão segura (texto) injetada pelo extra()
        if hasattr(obj, 'safe_data_abertura'):
            return obj.safe_data_abertura
        # Fallback: tenta acessar o original (pode falhar se corrompido)
        try:
            val = obj.data_abertura
            return val.isoformat() if val else None
        except Exception:
            return None

    def get_data_fim(self, obj):
        if hasattr(obj, 'safe_data_fim'):
            return obj.safe_data_fim
        try:
            val = obj.data_fim
            return val.isoformat() if val else None
        except Exception:
            return None

    def get_ultima_alteracao(self, obj):
        if hasattr(obj, 'safe_ultima_alteracao'):
            return obj.safe_ultima_alteracao
        try:
            val = obj.ultima_alteracao
            return val.isoformat() if val else None
        except Exception:
            return None
