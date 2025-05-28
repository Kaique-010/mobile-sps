from rest_framework import serializers
import base64
from .models import Produtos, UnidadeMedida, Tabelaprecos
from core.serializers import BancoContextMixin

class TabelaPrecoSerializer(BancoContextMixin, serializers.ModelSerializer):
    class Meta:
        model = Tabelaprecos
        fields = ['tabe_empr', 'tabe_fili', 'tabe_prod', 'tabe_prco', 'tabe_cuge', 'tabe_avis', 'tabe_apra']
        extra_kwargs = {
            'tabe_empr': {'read_only': True},
            'tabe_fili': {'read_only': True},
            'tabe_prod': {'read_only': True},
        }

    def create(self, validated_data):
        using = self.context.get('using')
        if using:
            return Tabelaprecos.objects.using(using).create(**validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        using = self.context.get('using')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if using:
            instance.save(using=using)
        else:
            instance.save()
        return instance


class ProdutoSerializer(BancoContextMixin, serializers.ModelSerializer):
    precos = serializers.SerializerMethodField()
    prod_preco_vista =  serializers.SerializerMethodField()
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

    def get_precos(self, obj):
        banco = self.context.get("banco")
        if not banco:
            return []

        precos = Tabelaprecos.objects.using(banco).filter(
            tabe_prod=obj.prod_codi,
            tabe_empr=obj.prod_empr,
        )

        return TabelaPrecoSerializer(precos, many=True, context=self.context).data
    
    
    def get_prod_preco_vista(self, obj):
        banco = self.context.get("banco")
        if not banco:
            return None

        preco = Tabelaprecos.objects.using(banco).filter(
            tabe_prod=obj.prod_codi,
            tabe_empr=obj.prod_empr
        ).values_list('tabe_avis', flat=True).first()

        return preco


        
    
    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")

        empresa = validated_data.get('prod_empr')
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
                    
                    novo_codigo = str(int(ultimo_produto.prod_codi) + 1)
                except ValueError:
                   
                    raise serializers.ValidationError({
                        'prod_codi': f'Não foi possível incrementar o código existente: {ultimo_produto.prod_codi}'
                    })
            else:
                print("Nenhum produto encontrado, iniciando com o código 1.")
                novo_codigo = "1"

           
           
            while Produtos.objects.using(banco).filter(prod_empr=empresa, prod_codi=novo_codigo).exists():
                print(f"O código {novo_codigo} já existe, tentando gerar um novo.")
                novo_codigo = str(int(novo_codigo) + 1)

            print(f"Código único gerado: {novo_codigo}")
            validated_data['prod_codi'] = novo_codigo

      
        return Produtos.objects.using(banco).create(**validated_data)

    

    def update_or_create_precos(self, produto, precos_data):
        banco = self.context.get("banco")
        if not banco:
            return

        for preco_data in precos_data:
            preco_data['tabe_prod'] = produto.prod_codi
            preco_data['tabe_empr'] = produto.prod_empr

            obj, created = Tabelaprecos.objects.using(banco).get_or_create(
                tabe_empr=preco_data['tabe_empr'],
                tabe_fili=preco_data['tabe_fili'],
                tabe_prod=preco_data['tabe_prod'],
                defaults=preco_data
            )
            if not created:
                for k, v in preco_data.items():
                    setattr(obj, k, v)
                obj.save(using=banco)




class UnidadeMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadeMedida
        fields = '__all__'

