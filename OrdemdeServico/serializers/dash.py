from rest_framework import serializers
from ..models import OrdensEletro

class OrdensEletroSerializer(serializers.ModelSerializer):
    total_os = serializers.DecimalField(source='total_orde', max_digits=12, decimal_places=2, read_only=True)
    status_ordem = serializers.CharField(source='status_orde', max_length=50, read_only=True)
    
    # Redefinir campos que podem vir vazios do banco legado para evitar erro de conversão int('')
    pedido_compra = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    nf_entrada = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = OrdensEletro
        fields = [
            'empresa', 'filial', 'ordem_de_servico', 'cliente', 'nome_cliente',
            'data_abertura', 'data_fim', 'setor', 'setor_nome', 'pecas', 'servicos',
            'total_orde', 'total_os', 'status_orde', 'status_ordem', 'responsavel', 
            'nome_responsavel', 'potencia', 'ultima_alteracao', 'pedido_compra', 'nf_entrada'
        ]
