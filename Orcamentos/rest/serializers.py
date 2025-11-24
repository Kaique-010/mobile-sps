from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from Licencas.models import Empresas
from Produtos.models import Produtos
from ..models import Orcamentos, ItensOrcamento
from Entidades.models import Entidades
from core.serializers import BancoContextMixin
from core.utils import calcular_valores_pedido, calcular_subtotal_item_bruto, calcular_total_item_com_desconto
from django.db.models import Prefetch
import logging
from decimal import Decimal, ROUND_HALF_UP
from parametros_admin.utils_pedidos import aplicar_descontos
from django.db import transaction
from django.db.models import Max

logger = logging.getLogger(__name__)


class ItemOrcamentoSerializer(BancoContextMixin, serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField()

    class Meta:
        model = ItensOrcamento
        fields = [
            'iped_prod', 'iped_quan', 'iped_suto', 'iped_unit', 'iped_tota',
            'iped_desc', 'iped_unli', 'iped_pdes_item', 'produto_nome'
        ]

    def to_internal_value(self, data):
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
    valor_subtotal = serializers.FloatField(source='pedi_topr', read_only=True)
    valor_desconto = serializers.FloatField(source='pedi_desc', read_only=True)
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
        self._entidades_cache = {}
        self._empresas_cache = {}

    def to_internal_value(self, data):
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
        if hasattr(obj, 'itens_prefetched'):
            itens = obj.itens_prefetched
        else:
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
        with transaction.atomic(using=banco):
            itens_data = validated_data.pop('itens_input', [])
            parametros = validated_data.pop('parametros', {})
            validated_data.pop('itens_data', None)

            valores = calcular_valores_pedido(
                itens_data,
                desconto_total=validated_data.get('pedi_desc'),
                desconto_percentual=parametros.get('desconto_percentual')
            )
            validated_data['pedi_topr'] = valores['subtotal']
            validated_data['pedi_desc'] = valores['desconto']
            validated_data['pedi_tota'] = valores['total']

            ultimo_orcamento = Orcamentos.objects.using(banco).aggregate(max_nume=Max('pedi_nume'))
            novo_nume = (ultimo_orcamento['max_nume'] or 0) + 1
            validated_data['pedi_nume'] = novo_nume

            orcamento = Orcamentos.objects.using(banco).create(**validated_data)

            itens_objs = []
            for idx, item_data in enumerate(itens_data, start=1):
                if 'iped_desc' not in item_data or item_data['iped_desc'] is None or isinstance(item_data['iped_desc'], bool):
                    item_data['iped_desc'] = 0.00
                subtotal_bruto = calcular_subtotal_item_bruto(
                    item_data.get('iped_quan', 0),
                    item_data.get('iped_unit', 0)
                )
                total_item = calcular_total_item_com_desconto(
                    item_data.get('iped_quan', 0),
                    item_data.get('iped_unit', 0),
                    item_data.get('iped_desc', 0)
                )
                item_data_clean = item_data.copy()
                item_data_clean.pop('iped_suto', None)
                item_data_clean.pop('iped_tota', None)
                item = ItensOrcamento.objects.using(banco).create(
                    iped_empr=orcamento.pedi_empr,
                    iped_fili=orcamento.pedi_fili,
                    iped_pedi=orcamento.pedi_nume,
                    iped_item=idx,
                    iped_data=orcamento.pedi_data,
                    iped_forn=orcamento.pedi_forn,
                    iped_suto=subtotal_bruto,
                    iped_tota=total_item,
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

    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não definido no contexto.")
        itens_data = validated_data.pop('itens_input', []) or validated_data.pop('itens', [])
        if not itens_data:
            raise ValidationError("Itens do orçamento são obrigatórios.")
        parametros = validated_data.pop('parametros', {})
        valores = calcular_valores_pedido(
            itens_data,
            desconto_total=validated_data.get('pedi_desc'),
            desconto_percentual=parametros.get('desconto_percentual')
        )
        validated_data['pedi_topr'] = valores['subtotal']
        validated_data['pedi_desc'] = valores['desconto']
        validated_data['pedi_tota'] = valores['total']
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)
        ItensOrcamento.objects.using(banco).filter(
            iped_empr=instance.pedi_empr,
            iped_fili=instance.pedi_fili,
            iped_pedi=str(instance.pedi_nume)
        ).delete()
        itens_objs = []
        for idx, item_data in enumerate(itens_data, start=1):
            if 'iped_desc' not in item_data or item_data['iped_desc'] is None or isinstance(item_data['iped_desc'], bool):
                item_data['iped_desc'] = 0.00
            subtotal_bruto = calcular_subtotal_item_bruto(
                item_data.get('iped_quan', 0),
                item_data.get('iped_unit', 0)
            )
            total_item = calcular_total_item_com_desconto(
                item_data.get('iped_quan', 0),
                item_data.get('iped_unit', 0),
                item_data.get('iped_desc', 0)
            )
            item_data_clean = item_data.copy()
            item_data_clean.pop('iped_suto', None)
            item_data_clean.pop('iped_tota', None)
            item = ItensOrcamento.objects.using(banco).create(
                iped_empr=instance.pedi_empr,
                iped_fili=instance.pedi_fili,
                iped_item=idx,
                iped_pedi=str(instance.pedi_nume),
                iped_data=instance.pedi_data,
                iped_forn=instance.pedi_forn,
                iped_suto=subtotal_bruto,
                iped_tota=total_item,
                **item_data_clean
            )
            itens_objs.append(item)
        aplicar_descontos(
            pedido=instance,
            itens=itens_objs,
            usar_desconto_item=parametros.get('usar_desconto_item', False),
            usar_desconto_total=parametros.get('usar_desconto_total', False),
            banco=banco
        )
        return instance

    def get_cliente_nome(self, obj):
        entidades_cache = self.context.get('entidades_cache')
        if entidades_cache:
            cache_key = f"{obj.pedi_forn}_{obj.pedi_empr}"
            return entidades_cache.get(cache_key)
        banco = self.context.get('banco')
        if not banco:
            return None
        try:
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
        empresas_cache = self.context.get('empresas_cache')
        if empresas_cache:
            return empresas_cache.get(obj.pedi_empr)
        banco = self.context.get('banco')
        if not banco:
            return None
        try:
            if obj.pedi_empr not in self._empresas_cache:
                empresa = Empresas.objects.using(banco).filter(empr_codi=obj.pedi_empr).first()
                self._empresas_cache[obj.pedi_empr] = empresa.empr_nome if empresa else None
            return self._empresas_cache[obj.pedi_empr]
        except Exception as e:
            logger.warning(f"Erro ao buscar empresa: {e}")
            return None