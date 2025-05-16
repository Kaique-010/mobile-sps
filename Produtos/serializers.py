from rest_framework import serializers
import base64
from .models import Produtos, UnidadeMedida
from core.serializers import BancoContextMixin

class ProdutoSerializer(BancoContextMixin, serializers.ModelSerializer):
    saldo_estoque = serializers.SerializerMethodField()
    imagem_base64 = serializers.SerializerMethodField()

    class Meta:
        model = Produtos
        fields = '__all__'
        read_only_fields = ['prod_codi']

    def get_saldo_estoque(self, obj):
        return getattr(obj, 'saldo_estoque', 0)
    
    def get_imagem_base64(self, obj):
        if obj.prod_foto:
            return base64.b64encode(obj.prod_foto).decode('utf-8')
        return None

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")

        empresa = validated_data.get('prod_empr')
        print(empresa)
        codigo = validated_data.get('prod_codi')

        if not codigo:
            print("Código não fornecido")

            ultimo_produto = (
                Produtos.objects.using(banco)  # Usando o banco correto
                .filter(prod_empr=empresa, prod_codi__regex=r'^\d+$')
                .order_by('-prod_codi')
                .first()
            )

            print(f"Último produto encontrado: {ultimo_produto}")

            if ultimo_produto:
                try:
                    # Incrementando o código do último produto
                    novo_codigo = str(int(ultimo_produto.prod_codi) + 1)
                except ValueError:
                    # Se o último código não puder ser incrementado, geramos erro
                    raise serializers.ValidationError({
                        'prod_codi': f'Não foi possível incrementar o código existente: {ultimo_produto.prod_codi}'
                    })
            else:
                print("Nenhum produto encontrado, iniciando com o código 1.")
                novo_codigo = "1"

            # Garantir que o novo código não exista já na tabela
            # A verificação será feita até que um código único seja encontrado
            while Produtos.objects.using(banco).filter(prod_empr=empresa, prod_codi=novo_codigo).exists():
                print(f"O código {novo_codigo} já existe, tentando gerar um novo.")
                novo_codigo = str(int(novo_codigo) + 1)

            print(f"Código único gerado: {novo_codigo}")
            validated_data['prod_codi'] = novo_codigo

        # Criar o produto diretamente sem transação atômica
        return super().create(validated_data)



class UnidadeMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadeMedida
        fields = '__all__'
