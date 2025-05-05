# produtos/serializers.py
from rest_framework import serializers
from django.db import transaction
from .models import Produtos
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

        if not empresa:
            raise serializers.ValidationError({'prod_empr': 'Empresa é obrigatória.'})

        if not codigo:
            # Lock REAL sobre o último produto da empresa
            ultimo_produto = (
                Produtos.objects
                .filter(prod_empr=empresa, prod_codi__regex=r'^\d+$')
                .select_for_update()
                .order_by('-prod_codi')
                .first()
            )

            if ultimo_produto:
                try:
                    novo_codigo = str(int(ultimo_produto.prod_codi) + 1)
                except ValueError:
                    raise serializers.ValidationError({
                        'prod_codi': f'Não foi possível incrementar o código existente: {ultimo_produto.prod_codi}'
                    })
            else:
                novo_codigo = "1"

            validated_data['prod_codi'] = novo_codigo
        else:
            # Valida se já existe o código para essa empresa
            if Produtos.objects.filter(prod_empr=empresa, prod_codi=codigo).exists():
                raise serializers.ValidationError({
                    'prod_codi': f'O código {codigo} já existe para a empresa {empresa}.'
                })

        return super().create(validated_data)
