# produtos/serializers.py
from rest_framework import serializers
from .models import Produtos

class ProdutoSerializer(serializers.ModelSerializer):
    saldo_estoque = serializers.SerializerMethodField()
    class Meta:
        model = Produtos
        fields = '__all__'
        read_only_fields = ['prod_codi']  # impede que seja enviado manualmente
    
    def get_saldo_estoque(self, obj):
      return getattr(obj, 'saldo_estoque', 0)

    def create(self, validated_data):
        empresa = validated_data['prod_empr']
        codigo = validated_data.get('prod_codi')

        if not codigo:
            # Se não veio código, gera automaticamente
            ultimo = Produtos.objects.filter(prod_empr=empresa, prod_codi__regex=r'^\d+$')\
                                    .order_by('-prod_codi')\
                                    .first()

            if ultimo:
                novo_codigo = str(int(ultimo.prod_codi) + 1).zfill(6)
            else:
                novo_codigo = "000001"

            validated_data['prod_codi'] = novo_codigo
        else:
            # Se veio código, valida se já existe para a empresa
            existe = Produtos.objects.filter(prod_empr=empresa, prod_codi=codigo).exists()
            if existe:
                raise serializers.ValidationError({
                    'prod_codi': f'O código {codigo} já existe para a empresa {empresa}.'
                })

        return super().create(validated_data)
