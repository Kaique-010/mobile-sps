from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from Licencas.models import Empresas
from Produtos.models import Produtos
from .models import Orcamentos, ItensOrcamento
from Entidades.models import Entidades
from core.serializers import BancoContextMixin
from core.utils import calcular_valores_pedido, calcular_subtotal_item_bruto, calcular_total_item_com_desconto 
from django.db.models import Prefetch
import logging
from decimal import Decimal, ROUND_HALF_UP
from parametros_admin.utils_pedidos import aplicar_descontos


logger = logging.getLogger(__name__)


class ItemOrcamentoSerializer(BancoContextMixin,serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField()
    
    class Meta:
        model = ItensOrcamento
        fields = [
            'iped_prod', 'iped_quan', 'iped_suto', 'iped_unit', 'iped_tota', 
            'iped_desc', 'iped_unli', 'iped_pdes_item', 'produto_nome'
        ]
    
    def to_internal_value(self, data):
        # Garante que iped_desc seja sempre um valor decimal
        if 'iped_desc' in data:
            if isinstance(data['iped_desc'], bool):
                data['iped_desc'] = 0.00 if not data['iped_desc'] else 0.00
            elif data['iped_desc'] is None:
                data['iped_desc'] = 0.00
            else:
                try:
                    data['iped_desc'] = round(float(data['iped_desc']), 2)
                except (ValueError, TypeError):
                    data['iped_desc'] = 0.00
        return super().to_internal_value(data)
    
    def get_produto_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            logger.warning("Banco não informado no context.")
            return None
        try:
            # Cache de produtos para evitar consultas repetidas
            if not hasattr(self, '_produtos_cache'):
                self._produtos_cache = {}
            
            cache_key = f"{obj.iped_prod}_{obj.iped_empr}"
            if cache_key not in self._produtos_cache:
                produto = Produtos.objects.using(banco).filter(
                    prod_codi=obj.iped_prod,
                    prod_empr=obj.iped_empr
                ).first()
                self._produtos_cache[cache_key] = produto.prod_nome if produto else None
            
            return self._produtos_cache[cache_key]
        except Exception as e:
            logger.error(f"Erro ao buscar produto: {e}")
            return None

            
class OrcamentosSerializer(BancoContextMixin, serializers.ModelSerializer):
    valor_total = serializers.FloatField(source='pedi_tota', read_only=True)
    valor_subtotal = serializers.FloatField(source='pedi_topr', read_only=True)  # Novo campo
    valor_desconto = serializers.FloatField(source='pedi_desc', read_only=True)  # Novo campo
    cliente_nome = serializers.SerializerMethodField(read_only=True)
    empresa_nome = serializers.SerializerMethodField(read_only=True)
    itens = serializers.SerializerMethodField(read_only=True)
    itens_input = ItemOrcamentoSerializer(many=True, write_only=True, required=False)
    itens_data = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    parametros = serializers.DictField(write_only=True, required=False)
    pedi_nume = serializers.IntegerField(read_only=True)  

    class Meta:
        model = Orcamentos
        fields = [
            'pedi_empr', 'pedi_fili', 'pedi_data', 'pedi_tota', 'pedi_forn', 'pedi_vend',
            'pedi_topr', 'pedi_desc',
            'itens', 'itens_input', 'itens_data',
            'valor_total', 'valor_subtotal', 'valor_desconto', 'cliente_nome', 'empresa_nome', 'pedi_nume',
            'parametros'
        ]
        extra_kwargs = {
            'pedi_nume': {'read_only': False},
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cache para entidades e empresas
        self._entidades_cache = {}
        self._empresas_cache = {}

    def to_internal_value(self, data):
        # Converte 'itens' para 'itens_input' se necessário
        if 'itens' in data and 'itens_input' not in data:
            data['itens_input'] = data.pop('itens')
        
        if 'pedi_tota' in data:
            try:
                data['pedi_tota'] = round(float(data['pedi_tota']), 2)
            except (ValueError, TypeError):
                pass
        return super().to_internal_value(data)
    
    def get_itens(self, obj):
        banco = self.context.get('banco')
        
        # Usar itens prefetched se disponível
        if hasattr(obj, 'itens_prefetched'):
            itens = obj.itens_prefetched
        else:
            # Fallback para consulta direta (otimizada)
            itens = ItensOrcamento.objects.using(banco).filter(
                iped_empr=obj.pedi_empr,
                iped_fili=obj.pedi_fili,
                iped_pedi=str(obj.pedi_nume)
            ).order_by('iped_item')
        
        return ItemOrcamentoSerializer(itens, many=True, context=self.context).data


    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        # Aceita tanto 'itens_input' quanto 'itens'
        itens_data = validated_data.pop('itens_input', []) or validated_data.pop('itens', [])
        if not itens_data:
            raise ValidationError("Itens do orçamento são obrigatórios.")

        parametros = validated_data.pop('parametros', {})

        # Calcular valores antes de criar o orçamento
        valores = calcular_valores_pedido(
            itens_data, 
            desconto_total=validated_data.get('pedi_desc'),
            desconto_percentual=parametros.get('desconto_percentual')
        )
        
        # Atualizar valores calculados
        validated_data['pedi_topr'] = valores['subtotal']  # Subtotal
        validated_data['pedi_desc'] = valores['desconto']  # Desconto
        validated_data['pedi_tota'] = valores['total']     # Total

        # Verificar se é edição (orçamento existente)
        orcamentos = None
        if 'pedi_nume' in validated_data:
            orcamentos = Orcamentos.objects.using(banco).filter(
                pedi_empr=validated_data['pedi_empr'],
                pedi_fili=validated_data['pedi_fili'],
                pedi_nume=validated_data['pedi_nume'],
            ).first()

        if orcamentos:
            # Edição: atualizar orçamento existente
            ItensOrcamento.objects.using(banco).filter(
                iped_empr=orcamentos.pedi_empr,
                iped_fili=orcamentos.pedi_fili,
                iped_pedi=str(orcamentos.pedi_nume)
            ).delete()

            for attr, value in validated_data.items():
                setattr(orcamentos, attr, value)
            orcamentos.save(using=banco)
            orcamento = orcamentos
        else:
            # Criação: buscar próximo número por empresa/filial
            ultimo = Orcamentos.objects.using(banco).filter(
                pedi_empr=validated_data['pedi_empr'],
                pedi_fili=validated_data['pedi_fili']
            ).order_by('-pedi_nume').first()
            
            proximo_numero = (ultimo.pedi_nume + 1) if ultimo else 1
            
            # Verificar se o número já existe (loop de segurança)
            while Orcamentos.objects.using(banco).filter(
                pedi_empr=validated_data['pedi_empr'],
                pedi_fili=validated_data['pedi_fili'],
                pedi_nume=proximo_numero
            ).exists():
                proximo_numero += 1
            
            validated_data['pedi_nume'] = proximo_numero
            orcamento = Orcamentos.objects.using(banco).create(**validated_data)

        itens_objs = []
        for idx, item_data in enumerate(itens_data, start=1):
            if 'iped_desc' not in item_data or item_data['iped_desc'] is None or isinstance(item_data['iped_desc'], bool):
                item_data['iped_desc'] = 0.00

            # Calcular subtotal bruto (quantidade × valor unitário)
            subtotal_bruto = calcular_subtotal_item_bruto(
                item_data.get('iped_quan', 0),
                item_data.get('iped_unit', 0)
            )
            
            # Calcular total do item com desconto
            total_item = calcular_total_item_com_desconto(
                item_data.get('iped_quan', 0),
                item_data.get('iped_unit', 0),
                item_data.get('iped_desc', 0)
            )


           # Remover campos que serão definidos explicitamente para evitar conflitos
            item_data_clean = item_data.copy()
            item_data_clean.pop('iped_suto', None)  # Remove se existir
            item_data_clean.pop('iped_tota', None)  # Remove se existir

            item = ItensOrcamento.objects.using(banco).create(
                iped_empr=orcamento.pedi_empr,
                iped_fili=orcamento.pedi_fili,
                iped_item=idx,
                iped_pedi=str(orcamento.pedi_nume),
                iped_data=orcamento.pedi_data,
                iped_forn=orcamento.pedi_forn,
                iped_suto=subtotal_bruto,  # Subtotal bruto (quantidade × valor unitário)
                iped_tota=total_item,      # Total com desconto aplicado
                **item_data_clean
            )
            itens_objs.append(item)

        aplicar_descontos(
            pedido=orcamento,
            itens=itens_objs,
            usar_desconto_item=parametros.get('usar_desconto_item', False),
            usar_desconto_total=parametros.get('usar_desconto_total', False),
            banco=banco
        )

        return orcamento

       

   

    def get_cliente_nome(self, obj):
        # Primeiro tentar usar o cache do contexto
        entidades_cache = self.context.get('entidades_cache')
        if entidades_cache:
            cache_key = f"{obj.pedi_forn}_{obj.pedi_empr}"
            return entidades_cache.get(cache_key)
        
        # Fallback para consulta individual
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            # Cache para evitar consultas repetidas
            cache_key = f"{obj.pedi_forn}_{obj.pedi_empr}"
            if cache_key not in self._entidades_cache:
                entidade = Entidades.objects.using(banco).filter(
                    enti_clie=obj.pedi_forn,
                    enti_empr=obj.pedi_empr,
                ).first()
                self._entidades_cache[cache_key] = entidade.enti_nome if entidade else None

            return self._entidades_cache[cache_key]

        except Exception as e:
            logger.warning(f"Erro ao buscar cliente: {e}")
            return None
        

    def get_empresa_nome(self, obj):
        # Primeiro tentar usar o cache do contexto
        empresas_cache = self.context.get('empresas_cache')
        if empresas_cache:
            return empresas_cache.get(obj.pedi_empr)
        
        # Fallback para consulta individual
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            # Cache para evitar consultas repetidas
            if obj.pedi_empr not in self._empresas_cache:
                empresa = Empresas.objects.using(banco).filter(empr_codi=obj.pedi_empr).first()
                self._empresas_cache[obj.pedi_empr] = empresa.empr_nome if empresa else None
            
            return self._empresas_cache[obj.pedi_empr]
        except Exception as e:
            logger.warning(f"Erro ao buscar empresa: {e}")
            return None