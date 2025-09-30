from datetime import datetime
from rest_framework import serializers
import base64
from .models import Produtos, UnidadeMedida, Tabelaprecos, ProdutosDetalhados, Marca
from core.serializers import BancoContextMixin
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import logging

logger = logging.getLogger(__name__)


class MarcaSerializer(BancoContextMixin, serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = ['codigo', 'nome']
    
    



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
            'field_log_data', 'field_log_time', 'tabe_hist', 'tabe_entr'
        ]
        extra_kwargs = {
            'tabe_empr': {'read_only': True},
            'tabe_fili': {'read_only': True},
            'tabe_prod': {'read_only': True},
            'field_log_data': {'read_only': True},
            'field_log_time': {'read_only': True},
        }

    def to_internal_value(self, data):
        # Converter strings vazias para None antes da validação
        decimal_fields = [
            'tabe_prco', 'tabe_icms', 'tabe_desc', 'tabe_vipi', 'tabe_pipi',
            'tabe_fret', 'tabe_desp', 'tabe_cust', 'tabe_marg', 'tabe_impo',
            'tabe_avis', 'tabe_praz', 'tabe_apra', 'tabe_vare', 'tabe_valo_st',
            'tabe_perc_reaj', 'tabe_cuge', 'tabe_perc_st'
        ]
        
        for field in decimal_fields:
            if field in data and (data[field] == '' or data[field] is None):
                data[field] = None
                
        return super().to_internal_value(data)

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

    

    
    def to_representation(self, instance):
        """Validar dados antes da serialização"""
        # Verificar se tabe_entr tem data válida
        if hasattr(instance, 'tabe_entr') and instance.tabe_entr:
            try:
                year = instance.tabe_entr.year
                if year < 1900 or year > 2100:
                    logger.warning(f"Data inválida em tabe_entr: {instance.tabe_entr} - Produto: {instance.tabe_prod}")
                    instance.tabe_entr = None
            except (ValueError, AttributeError) as e:
                logger.warning(f"Erro na data tabe_entr: {e} - Produto: {instance.tabe_prod}")
                instance.tabe_entr = None
        
        return super().to_representation(instance)
class ProdutoSerializer(BancoContextMixin, serializers.ModelSerializer):
    precos = serializers.SerializerMethodField()
    prod_preco_vista = serializers.SerializerMethodField()
    prod_preco_normal = serializers.SerializerMethodField()
    saldo_estoque = serializers.SerializerMethodField()
    imagem_base64 = serializers.SerializerMethodField()
    preco_principal = serializers.SerializerMethodField()
    # Sobrescrever campos decimais problemáticos
    prod_cera_m2cx = serializers.SerializerMethodField()
    prod_cera_pccx = serializers.SerializerMethodField()

    class Meta:
        model = Produtos
        fields = '__all__'
        read_only_fields = ['prod_codi']
    
    def safe_decimal_conversion(self, value, default=None):
        """Converte valores para Decimal de forma segura"""
        if value is None:
            return default
        
        try:
            # Remove espaços em branco
            if isinstance(value, str):
                value = value.strip()
                if not value:  # String vazia
                    return default
            
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return default
    
    def get_prod_preco_vista(self, obj):
        """Retorna preço à vista de forma segura"""
        return self.safe_decimal_conversion(getattr(obj, 'prod_preco_vista', None), Decimal('0.00'))
    
    def get_prod_preco_normal(self, obj):
        """Retorna preço normal de forma segura"""
        return self.safe_decimal_conversion(getattr(obj, 'prod_preco_normal', None), Decimal('0.00'))
        
    def get_saldo_estoque(self, obj):
        """Retorna saldo de estoque de forma segura"""
        saldo = getattr(obj, 'saldo_estoque', 0)
        return self.safe_decimal_conversion(saldo, Decimal('0.00'))
    
    def get_prod_cera_m2cx(self, obj):
        """Retorna m²/caixa de forma segura"""
        return self.safe_decimal_conversion(obj.prod_cera_m2cx, Decimal('0.00'))
    
    def get_prod_cera_pccx(self, obj):
        """Retorna peças/caixa de forma segura"""
        return self.safe_decimal_conversion(obj.prod_cera_pccx, Decimal('0.00'))

    def validate(self, attrs):
        if not attrs.get("prod_codi") and Produtos.objects.filter(prod_codi='', prod_empr=attrs.get("prod_empr")).exists():
            raise serializers.ValidationError("Produto com código vazio já existe para esta empresa.")
        
        # Sempre definir prod_orig_merc como '0' (origem nacional)
        attrs['prod_orig_merc'] = '0'
        
        # Sincronizar prod_codi_nume com prod_codi
        if 'prod_codi' in attrs:
            attrs['prod_codi_nume'] = attrs['prod_codi']
        
        # Converter strings vazias em None para todos os campos decimais possíveis
        decimal_fields = [
            'prod_cera_m2cx', 'prod_cera_pccx',
            # Campos de preço que podem vir no request
            'preco_vista', 'preco_prazo', 'custo', 'saldo',
            'peso_bruto', 'peso_liquido', 'valor_total_estoque',
            'valor_total_venda_vista', 'valor_total_venda_prazo'
        ]
        
        for field in decimal_fields:
            if field in attrs and (attrs[field] == '' or attrs[field] is None):
                attrs[field] = None
                
        return attrs


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
        ).values('tabe_avis', 'tabe_apra', 'tabe_prco')
        return list(precos)

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")

        # Garantir que prod_orig_merc seja sempre '0'
        validated_data['prod_orig_merc'] = '0'

        prod_empr = validated_data.get('prod_empr')
        prod_codi = validated_data.get('prod_codi')

        # Se veio código, tenta atualizar
        if prod_codi:
            # Sincronizar prod_codi_nume com prod_codi
            validated_data['prod_codi_nume'] = prod_codi
            
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
        # Sincronizar prod_codi_nume com o novo prod_codi
        validated_data['prod_codi_nume'] = str(proximo_codigo)

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
        banco = self.get_banco()
        
        # Garantir que prod_orig_merc seja sempre '0'
        validated_data['prod_orig_merc'] = '0'
        
        # Sincronizar prod_codi_nume com prod_codi se prod_codi foi alterado
        if 'prod_codi' in validated_data:
            validated_data['prod_codi_nume'] = validated_data['prod_codi']
        
        # Limpar campos decimais que podem vir como string vazia
        if validated_data.get('prod_cera_m2cx') == '':
            validated_data['prod_cera_m2cx'] = None
            instance.prod_cera_m2cx = None
        
        if validated_data.get('prod_cera_pccx') == '':
            validated_data['prod_cera_pccx'] = None
            instance.prod_cera_pccx = None
        
        print("=== ANTES DO SAVE ===")
        print(f"Campo decimal prod_cera_m2cx: {instance.prod_cera_m2cx} (type: {type(instance.prod_cera_m2cx)})")
        print(f"Campo decimal prod_cera_pccx: {instance.prod_cera_pccx} (type: {type(instance.prod_cera_pccx)})")
        
        # CORREÇÃO: Usar update() direto no queryset para chave composta
        from .models import Produtos
        Produtos.objects.using(banco).filter(
            prod_codi=instance.prod_codi,
            prod_empr=instance.prod_empr
        ).update(**validated_data)
        
        # Recarregar a instância especificando os campos da chave composta
        instance = Produtos.objects.using(banco).get(
            prod_codi=instance.prod_codi,
            prod_empr=instance.prod_empr
        )
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

    def to_internal_value(self, data):
        # Converter strings vazias para None antes da validação
        decimal_fields = [
            'prod_cera_m2cx', 'prod_cera_pccx',
            'preco_vista', 'preco_prazo', 'custo', 'saldo',
            'peso_bruto', 'peso_liquido'
        ]
        
        for field in decimal_fields:
            if field in data and data[field] == '':
                data[field] = None
                
        return super().to_internal_value(data)
