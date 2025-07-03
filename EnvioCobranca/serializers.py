import rest_framework.serializers as serializers
from .models import EnviarCobranca


class EnviarCobrancaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnviarCobranca
        fields = '__all__'
        read_only_fields = ('empresa', 'filial', 'cliente_id', 'cliente_nome', 'cliente_celular', 'cliente_telefone', 'cliente_email', 'numero_titulo', 'serie', 'parcela', 'vencimento', 'valor', 'forma_recebimento_codigo', 'forma_recebimento_nome', 'linha_digitavel', 'url_boleto')
