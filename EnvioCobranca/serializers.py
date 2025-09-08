import base64
from rest_framework import serializers
from .models import EnviarCobranca

class EnviarCobrancaSerializer(serializers.ModelSerializer):
    boleto_base64 = serializers.SerializerMethodField()

    class Meta:
        model = EnviarCobranca
        fields = '__all__'
        read_only_fields = (
            'empresa', 'filial', 'cliente_id', 'cliente_nome',
            'cliente_celular', 'cliente_telefone', 'cliente_email',
            'numero_titulo', 'serie', 'parcela', 'vencimento',
            'valor', 'forma_recebimento_codigo', 'forma_recebimento_nome',
            'url_boleto', 'boleto'
        )
    
    def get_boleto_base64(self, obj):
        """Converte o boleto binário em base64 se existir e se solicitado"""
        # Verificar se foi solicitado incluir boleto
        request = self.context.get('request')
        incluir_boleto = request.query_params.get('incluir_boleto') == 'true' if request else False
        
        if incluir_boleto and obj.boleto:
            return base64.b64encode(obj.boleto).decode('utf-8')
        return None

   