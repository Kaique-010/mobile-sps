# produtos/serializers.py
from rest_framework import serializers
from django.db import transaction
from .models import Produtos, UnidadeMedida
from django.db import connection

class ProdutoSerializer(serializers.ModelSerializer):
    saldo_estoque = serializers.SerializerMethodField()

    class Meta:
        model = Produtos
        fields = '__all__'
        read_only_fields = ['prod_codi']

    def get_saldo_estoque(self, obj):
        return getattr(obj, 'saldo_estoque', 0)

    @transaction.atomic
    def create(self, validated_data):
        empresa = validated_data.get('prod_empr')
        codigo = validated_data.get('prod_codi')

        if not codigo:
            print("Código não fornecido")
            ultimo_produto = (
                Produtos.objects
                .filter(prod_empr=empresa, prod_codi__regex=r'^\d+$')
                .select_for_update()
                .order_by('-prod_codi')
                .first()
            )
            print(f"Último produto encontrado: {ultimo_produto}")
            if ultimo_produto:
                try:
                    novo_codigo = str(int(ultimo_produto.prod_codi) + 1)
                except ValueError:
                    raise serializers.ValidationError({
                        'prod_codi': f'Não foi possível incrementar o código existente: {ultimo_produto.prod_codi}'
                    })
            else:
                print("Nenhum produto encontrado, iniciando com o código 1.")
                novo_codigo = "1"
            print(f"Novo código gerado: {novo_codigo}")
            
            # Verificar se o código gerado já existe para a empresa
            while Produtos.objects.filter(prod_empr=empresa, prod_codi=novo_codigo).exists():
                print(f"O código {novo_codigo} já existe, tentando gerar um novo.")
                novo_codigo = str(int(novo_codigo) + 1)
                
            print(f"Código único gerado: {novo_codigo}")
            validated_data['prod_codi'] = novo_codigo
        
        return super().create(validated_data)


class UnidadeMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadeMedida
        fields = '__all__'
