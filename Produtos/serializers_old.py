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
    prod_foto = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    prod_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)    
    imagem_base64 = serializers.SerializerMethodField()
    preco_principal = serializers.SerializerMethodField()
    # Campos com representação segura (permitindo valores inválidos no banco sem quebrar a listagem)
    prod_cera_m2cx = serializers.SerializerMethodField()
    prod_cera_pccx = serializers.SerializerMethodField()
    prod_cera_kgcx = serializers.SerializerMethodField()

    class Meta:
        model = Produtos
        fields = '__all__'
        read_only_fields = ['prod_codi']
        extra_kwargs = {}
    
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
        return self.safe_decimal_conversion(getattr(obj, 'prod_cera_m2cx', None), Decimal('0.00'))

    def get_prod_cera_pccx(self, obj):
        """Retorna peças/caixa de forma segura"""
        return self.safe_decimal_conversion(getattr(obj, 'prod_cera_pccx', None), Decimal('0.00'))

    def get_prod_cera_kgcx(self, obj):
        """Retorna kg/caixa de forma segura"""
        return self.safe_decimal_conversion(getattr(obj, 'prod_cera_kgcx', None), Decimal('0.00'))

    def to_internal_value(self, data):
        """Normaliza entradas antes da validação de campo (blank -> None)."""
        decimal_fields = [
            'prod_cera_m2cx', 'prod_cera_pccx', 'prod_cera_kgcx',
            # Campos opcionais que podem vir em requests
            'preco_vista', 'preco_prazo', 'custo', 'saldo',
            'peso_bruto', 'peso_liquido', 'valor_total_estoque',
            'valor_total_venda_vista', 'valor_total_venda_prazo'
        ]
        for field in decimal_fields:
            if field in data and (data[field] == '' or data[field] is None):
                data[field] = None
        return super().to_internal_value(data)

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
            'prod_cera_m2cx', 'prod_cera_pccx', 'prod_cera_kgcx',
            # Campos de preço que podem vir no request
            'preco_vista', 'preco_prazo', 'custo', 'saldo',
            'peso_bruto', 'peso_liquido', 'valor_total_estoque',
            'valor_total_venda_vista', 'valor_total_venda_prazo'
        ]
        
        for field in decimal_fields:
            if field in attrs and (attrs[field] == '' or attrs[field] is None):
                attrs[field] = None
                
        return attrs
    
    def validate_campos_servico(self, attrs):
        if attrs.get("prod_e_serv"):
            if attrs.get("prod_exig_iss") not in [1, 2, 3, 4]:
                raise serializers.ValidationError("Quando é serviço, prod_exig_iss deve ser 1, 2, 3 ou 4.")
            if attrs.get("prod_cnae") is None:
                raise serializers.ValidationError("Quando é serviço, cnae é obrigatório.")
            if attrs.get("prod_codi_serv") is None:
                raise serializers.ValidationError("Quando é serviço, código do serviço é obrigatório.")
        return attrs


    def get_imagem_base64(self, obj):
        if obj.prod_foto:
            data = obj.prod_foto.tobytes() if isinstance(obj.prod_foto, memoryview) else obj.prod_foto
            return base64.b64encode(data).decode('utf-8')
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

        # Mesclar valores brutos dos campos decimais a partir do request inicial
        try:
            raw_m2cx = self.initial_data.get('prod_cera_m2cx', None)
            if raw_m2cx not in (None, ''):
                validated_data['prod_cera_m2cx'] = Decimal(str(raw_m2cx).replace(',', '.'))
        except Exception:
            validated_data['prod_cera_m2cx'] = None

        try:
            raw_pccx = self.initial_data.get('prod_cera_pccx', None)
            if raw_pccx not in (None, ''):
                validated_data['prod_cera_pccx'] = Decimal(str(raw_pccx).replace(',', '.'))
        except Exception:
            validated_data['prod_cera_pccx'] = None

        try:
            raw_kgcx = self.initial_data.get('prod_cera_kgcx', None)
            if raw_kgcx not in (None, ''):
                validated_data['prod_cera_kgcx'] = Decimal(str(raw_kgcx).replace(',', '.'))
        except Exception:
            validated_data['prod_cera_kgcx'] = None

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
        
        # Remover campos da chave primária composta do validated_data para evitar erro de duplicidade
        # em bancos que validam update mesmo com o mesmo valor (ou se o usuário tentar mudar)
        validated_data.pop('prod_empr', None)
        validated_data.pop('prod_codi', None)
        
        # Garantir que prod_orig_merc seja sempre '0'
        validated_data['prod_orig_merc'] = '0'
        
        # Sincronizar prod_codi_nume com prod_codi se prod_codi foi alterado
        if 'prod_codi' in validated_data:
            validated_data['prod_codi_nume'] = validated_data['prod_codi']
        
        # Mesclar valores dos campos decimais a partir do request inicial
        raw_m2cx = self.initial_data.get('prod_cera_m2cx', None)
        if raw_m2cx == '':
            validated_data['prod_cera_m2cx'] = None
            instance.prod_cera_m2cx = None
        elif raw_m2cx is not None:
            try:
                validated_data['prod_cera_m2cx'] = Decimal(str(raw_m2cx).replace(',', '.'))
            except Exception:
                validated_data['prod_cera_m2cx'] = None
                instance.prod_cera_m2cx = None

        raw_pccx = self.initial_data.get('prod_cera_pccx', None)
        if raw_pccx == '':
            validated_data['prod_cera_pccx'] = None
            instance.prod_cera_pccx = None
        elif raw_pccx is not None:
            try:
                validated_data['prod_cera_pccx'] = Decimal(str(raw_pccx).replace(',', '.'))
            except Exception:
                validated_data['prod_cera_pccx'] = None
                instance.prod_cera_pccx = None

        raw_kgcx = self.initial_data.get('prod_cera_kgcx', None)
        if raw_kgcx == '':
            validated_data['prod_cera_kgcx'] = None
            instance.prod_cera_kgcx = None
        elif raw_kgcx is not None:
            try:
                validated_data['prod_cera_kgcx'] = Decimal(str(raw_kgcx).replace(',', '.'))
            except Exception:
                validated_data['prod_cera_kgcx'] = None
                instance.prod_cera_kgcx = None

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
    
    def validate_prod_foto(self, value):
        """Converte base64 em binário antes de salvar"""
        if not value or (isinstance(value, str) and not value.strip()):
            return None
        try:
            if isinstance(value, str) and ',' in value:
                # Remove cabeçalho 'data:image/jpeg;base64,' se existir
                value = value.split(',', 1)[1]
            return base64.b64decode(value)
        except Exception as e:
            raise serializers.ValidationError(f"Erro ao decodificar imagem: {str(e)}")


class ProdutoServicoSerializer(serializers.ModelSerializer):
    """
    Serializer específico para atualizar campos de serviço de um produto.
    """
    class Meta:
        model = Produtos
        fields = [
            'prod_e_serv', 
            'prod_exig_iss', 
            'prod_iss', 
            'prod_codi_serv', 
            'prod_desc_serv', 
            'prod_cnae', 
            'prod_list_tabe_prec',
            'prod_ncm'
        ]

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        
        # Helper to get value from attrs or instance
        def get_val(key):
            if key in attrs:
                return attrs[key]
            if instance:
                return getattr(instance, key)
            return None

        is_service = get_val("prod_e_serv")
        
        if is_service:
            exig_iss = get_val("prod_exig_iss")
            if exig_iss not in [1, 2, 3, 4]:
                raise serializers.ValidationError({"prod_exig_iss": "Quando é serviço, prod_exig_iss deve ser 1, 2, 3 ou 4."})
            
            # Se prod_cnae estiver em branco no attrs ou não enviado mas nulo no banco
            cnae = get_val("prod_cnae")
            if not cnae:
                raise serializers.ValidationError({"prod_cnae": "Quando é serviço, cnae é obrigatório."})
            
            codi_serv = get_val("prod_codi_serv")
            if not codi_serv:
                raise serializers.ValidationError({"prod_codi_serv": "Quando é serviço, código do serviço é obrigatório."})
        
        return attrs


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
            'prod_cera_m2cx', 'prod_cera_pccx','prod_cera_kgcx',
            'preco_vista', 'preco_prazo', 'custo', 'saldo',
            'peso_bruto', 'peso_liquido','ncm'
        ]
        
        for field in decimal_fields:
            if field in data and data[field] == '':
                data[field] = None
                
        return super().to_internal_value(data)


class ProdutoEtiquetasSerializer(serializers.Serializer):
    produtos = serializers.ListField(
        child=serializers.CharField(max_length=50),
        allow_empty=False
    )

    def validate_produtos(self, value):
        produtos = [p.strip() for p in value if p.strip()]
        if not produtos:
            raise serializers.ValidationError("Lista de produtos vazia.")
        return list(set(produtos))