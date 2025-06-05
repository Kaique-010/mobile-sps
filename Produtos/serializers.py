from rest_framework import serializers
import base64
from .models import Produtos, UnidadeMedida, Tabelaprecos
from core.serializers import BancoContextMixin

class TabelaPrecoSerializer(BancoContextMixin, serializers.ModelSerializer):
    percentual_avis = serializers.FloatField(write_only=True, required=False)
    percentual_apra = serializers.FloatField(write_only=True, required=False)

    class Meta:
        model = Tabelaprecos
        fields = [
            'tabe_empr', 'tabe_fili', 'tabe_prod', 
            'tabe_prco', 'tabe_cuge', 'tabe_avis', 'tabe_apra',
            'tabe_desc', 'tabe_marg', 'tabe_vare',
            'tabe_cust', 'tabe_icms', 'tabe_valo_st',
            'percentual_avis', 'percentual_apra'
        ]
        extra_kwargs = {
            'tabe_empr': {'read_only': True},
            'tabe_fili': {'read_only': True},
            'tabe_prod': {'read_only': True},
        }

    def validate(self, data):
        # Validar se os preços são positivos
        campos_preco = ['tabe_prco', 'tabe_avis', 'tabe_apra', 'tabe_cuge', 'tabe_vare']
        for campo in campos_preco:
            if campo in data and data[campo] and data[campo] < 0:
                raise serializers.ValidationError({campo: "O preço não pode ser negativo"})
        
        # Calcular preços baseados nos percentuais
        if 'tabe_prco' in data:
            preco_base = data['tabe_prco']
            
            if 'percentual_avis' in data:
                percentual = data.pop('percentual_avis')
                data['tabe_avis'] = round(preco_base * (1 + percentual / 100), 2)
            
            if 'percentual_apra' in data:
                percentual = data.pop('percentual_apra')
                data['tabe_apra'] = round(preco_base * (1 + percentual / 100), 2)

        return data

    def create(self, validated_data):
        using = self.context.get('using') or self.context.get('banco')
        if not using:
            raise serializers.ValidationError("Banco de dados não especificado")

        # Verificar se já existe um registro
        try:
            instance = Tabelaprecos.objects.using(using).get(
                tabe_empr=validated_data['tabe_empr'],
                tabe_fili=validated_data['tabe_fili'],
                tabe_prod=validated_data['tabe_prod']
            )
            # Atualizar o existente
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save(using=using)
            return instance
        except Tabelaprecos.DoesNotExist:
            # Criar novo
            return Tabelaprecos.objects.using(using).create(**validated_data)

    def update(self, instance, validated_data):
        using = self.context.get('using') or self.context.get('banco')
        if not using:
            raise serializers.ValidationError("Banco de dados não especificado")

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=using)
        return instance


class ProdutoSerializer(BancoContextMixin, serializers.ModelSerializer):
    precos = TabelaPrecoSerializer(many=True, read_only=True)
    prod_preco_vista = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    saldo_estoque = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    imagem_base64 = serializers.SerializerMethodField()
    preco_principal = serializers.SerializerMethodField()

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

    def get_preco_principal(self, obj):
        """Retorna o preço principal do produto (à vista ou normal)"""
        banco = self.context.get("banco")
        if not banco:
            return None

        preco = Tabelaprecos.objects.using(banco).filter(
            tabe_prod=obj.prod_codi,
            tabe_empr=obj.prod_empr
        ).values('tabe_avis', 'tabe_prco').first()

        if preco:
            return preco['tabe_avis'] if preco['tabe_avis'] else preco['tabe_prco']
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

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")

        # Criar produto
        produto = super().create(validated_data)

        # Criar tabela de preço padrão se não existir
        precos_data = self.context.get('precos_data', {})
        if precos_data:
            TabelaPrecoSerializer(context=self.context).create({
                'tabe_empr': produto.prod_empr,
                'tabe_fili': 1,  # Filial padrão
                'tabe_prod': produto.prod_codi,
                **precos_data
            })

        return produto

    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")

        # Atualizar produto
        produto = super().update(instance, validated_data)

        # Atualizar preços se fornecidos
        precos_data = self.context.get('precos_data')
        if precos_data:
            try:
                tabela_preco = Tabelaprecos.objects.using(banco).get(
                    tabe_empr=produto.prod_empr,
                    tabe_fili=1,
                    tabe_prod=produto.prod_codi
                )
                TabelaPrecoSerializer(tabela_preco, data=precos_data, context=self.context).update(
                    tabela_preco, precos_data
                )
            except Tabelaprecos.DoesNotExist:
                TabelaPrecoSerializer(context=self.context).create({
                    'tabe_empr': produto.prod_empr,
                    'tabe_fili': 1,
                    'tabe_prod': produto.prod_codi,
                    **precos_data
                })

        return produto


class UnidadeMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadeMedida
        fields = '__all__'

