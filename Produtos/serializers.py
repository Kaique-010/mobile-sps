from rest_framework import serializers
import base64
from .models import Produtos, UnidadeMedida, Tabelaprecos, ProdutosDetalhados
from core.serializers import BancoContextMixin
from decimal import Decimal, ROUND_HALF_UP

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
            'percentual_avis', 'percentual_apra',
            'field_log_data', 'field_log_time', 'tabe_hist'
        ]
        extra_kwargs = {
            'tabe_empr': {'read_only': True},
            'tabe_fili': {'read_only': True},
            'tabe_prod': {'read_only': True},
            'field_log_data': {'read_only': True},
            'field_log_time': {'read_only': True},
        }

    def validate(self, data):
        campos_preco = ['tabe_prco', 'tabe_avis', 'tabe_apra', 'tabe_cuge', 'tabe_vare']
        for campo in campos_preco:
            valor = data.get(campo)
            if valor is not None and Decimal(valor) < 0:
                raise serializers.ValidationError({campo: "O preço não pode ser negativo"})

        if 'tabe_prco' in data:
            preco_base = Decimal(data['tabe_prco'])
            if 'percentual_avis' in data:
                percentual = Decimal(str(data.pop('percentual_avis')))
                data['tabe_avis'] = (preco_base * (Decimal('1') + percentual / 100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if 'percentual_apra' in data:
                percentual = Decimal(str(data.pop('percentual_apra')))
                data['tabe_apra'] = (preco_base * (Decimal('1') + percentual / 100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return data

    def create(self, validated_data):
        using = self.context.get('using') or self.context.get('banco')
        if not using:
            raise serializers.ValidationError("Banco de dados não especificado")

        # garante que as chaves existem, pegando do contexto se não vier no validated_data
        tabe_empr = validated_data.get('tabe_empr') or self.context.get('tabe_empr')
        tabe_fili = validated_data.get('tabe_fili') or self.context.get('tabe_fili')
        tabe_prod = validated_data.get('tabe_prod') or self.context.get('tabe_prod')

        if not all([tabe_empr, tabe_fili, tabe_prod]):
            raise serializers.ValidationError("Campos tabe_empr, tabe_fili e tabe_prod são obrigatórios")

        try:
            instance = Tabelaprecos.objects.using(using).get(
                tabe_empr=tabe_empr,
                tabe_fili=tabe_fili,
                tabe_prod=tabe_prod
            )
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save(using=using)
            return instance
        except Tabelaprecos.DoesNotExist:
            # adiciona os campos obrigatórios no validated_data antes de criar
            validated_data['tabe_empr'] = tabe_empr
            validated_data['tabe_fili'] = tabe_fili
            validated_data['tabe_prod'] = tabe_prod
            return Tabelaprecos.objects.using(using).create(**validated_data)


    def update(self, instance, validated_data):
        using = self.context.get('using') or self.context.get('banco')
        if not using:
            raise serializers.ValidationError("Banco de dados não especificado")

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=using, force_update=True)
        return instance


class ProdutoSerializer(BancoContextMixin, serializers.ModelSerializer):
    precos = serializers.SerializerMethodField()
    prod_preco_vista = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    prod_preco_normal = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    saldo_estoque = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    imagem_base64 = serializers.SerializerMethodField()
    preco_principal = serializers.SerializerMethodField()

    class Meta:
        model = Produtos
        fields = '__all__'
        read_only_fields = ['prod_codi']
        
    def validate(self, attrs):
        if not attrs.get("prod_codi") and Produtos.objects.filter(prod_codi='', prod_empr=attrs.get("prod_empr")).exists():
            raise serializers.ValidationError("Produto com código vazio já existe para esta empresa.")
        return attrs


    def get_saldo_estoque(self, obj):
        return getattr(obj, 'saldo_estoque', 0)

    def get_imagem_base64(self, obj):
        if obj.prod_foto:
            return base64.b64encode(obj.prod_foto).decode('utf-8')
        return None

    def get_preco_principal(self, obj):
        if hasattr(obj, 'prod_preco_vista') and obj.prod_preco_vista:
            return obj.prod_preco_vista
        if hasattr(obj, 'prod_preco_normal') and obj.prod_preco_normal:
            return obj.prod_preco_normal

        banco = self.context.get("banco")
        if not banco:
            return None

        preco = Tabelaprecos.objects.using(banco).filter(
            tabe_prod=obj.prod_codi,
            tabe_empr=obj.prod_empr
        ).values('tabe_avis', 'tabe_prco').first()

        if preco:
            return preco['tabe_avis'] or preco['tabe_prco']
        return None

    def get_precos(self, obj):
        banco = self.context.get("banco")
        if not banco:
            return []
        precos = Tabelaprecos.objects.using(banco).filter(
            tabe_prod=obj.prod_codi,
            tabe_empr=obj.prod_empr
        )
        return TabelaPrecoSerializer(precos, many=True, context=self.context).data

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")

        prod_empr = validated_data.get('prod_empr')
        prod_codi = validated_data.get('prod_codi')

        # Se veio código, tenta atualizar
        if prod_codi:
            try:
                produto_existente = Produtos.objects.using(banco).get(
                    prod_codi=prod_codi,
                    prod_empr=prod_empr
                )
                for attr, value in validated_data.items():
                    setattr(produto_existente, attr, value)
                produto_existente.save(using=banco)
                return produto_existente
            except Produtos.DoesNotExist:
                pass  # Vai criar novo

        # Geração de código sequencial sem zero à esquerda e sem colisão
        ultimo = Produtos.objects.using(banco).filter(
            prod_empr=prod_empr
        ).order_by('-prod_codi').first()

        proximo_codigo = int(ultimo.prod_codi) + 1 if ultimo and str(ultimo.prod_codi).isdigit() else 1

        while Produtos.objects.using(banco).filter(prod_codi=str(proximo_codigo), prod_empr=prod_empr).exists():
            proximo_codigo += 1

        validated_data['prod_codi'] = str(proximo_codigo)

        produto = Produtos.objects.using(banco).create(**validated_data)

        # Cria preços se veio no contexto
        precos_data = self.context.get('precos_data')
        if precos_data:
            precos_data.update({
                'tabe_empr': produto.prod_empr,
                'tabe_fili': produto.prod_fili,
                'tabe_prod': produto.prod_codi,
            })
            preco_serializer = TabelaPrecoSerializer(data=precos_data, context=self.context)
            preco_serializer.is_valid(raise_exception=True)
            preco_serializer.save()

        return produto





    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)

        precos_data = self.context.get('precos_data')
        if precos_data:
            try:
                tabela_preco = Tabelaprecos.objects.using(banco).get(
                    tabe_empr=instance.prod_empr,
                    tabe_fili=instance.prod_fili,
                    tabe_prod=instance.prod_codi
                )
                TabelaPrecoSerializer(tabela_preco, data=precos_data, context=self.context).update(
                    tabela_preco, precos_data
                )
            except Tabelaprecos.DoesNotExist:
                TabelaPrecoSerializer(context=self.context).create({
                    'tabe_empr': instance.prod_empr,
                    'tabe_fili': instance.prod_fili,
                    'tabe_prod': instance.prod_codi,
                    **precos_data
                })

        return instance


class UnidadeMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadeMedida
        fields = '__all__'


class ProdutoDetalhadoSerializer(serializers.ModelSerializer):
    imagem_base64 = serializers.SerializerMethodField()
    
    class Meta:
        model = ProdutosDetalhados
        fields = '__all__'
    
    def get_imagem_base64(self, obj):
            if obj.foto:
                return base64.b64encode(obj.foto).decode('utf-8')
            return None
