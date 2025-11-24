from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from datetime import datetime
from Licencas.models import Empresas
from Produtos.models import Produtos
from ..models import PedidoVenda, Itenspedidovenda, PedidosGeral
from Entidades.models import Entidades
from core.serializers import BancoContextMixin
from core.utils import calcular_valores_pedido, calcular_subtotal_item_bruto, calcular_total_item_com_desconto
from ParametrosSps.services.pedidos_service import PedidosService
from parametros_admin.utils_pedidos import aplicar_descontos
from .views_financeiro import GerarTitulosPedidoView, RemoverTitulosPedidoView, ConsultarTitulosPedidoView, RelatorioFinanceiroPedidoView
import logging

logger = logging.getLogger(__name__)


class ItemPedidoVendaSerializer(BancoContextMixin, serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField()

    class Meta:
        model = Itenspedidovenda
        fields = [
            'iped_prod', 'iped_quan', 'iped_unit', 'iped_fret', 'iped_desc',
            'iped_unli', 'iped_cust', 'iped_tipo', 'iped_desc_item',
            'iped_perc_desc', 'iped_unme', 'produto_nome'
        ]

    def get_produto_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            logger.warning("Banco não informado no context.")
            return None
        try:
            produto = Produtos.objects.using(banco).filter(
                prod_codi=obj.iped_prod,
                prod_empr=obj.iped_empr
            ).first()
            return produto.prod_nome if produto else None
        except Exception as e:
            logger.error(f"Erro ao buscar produto: {e}")
            return None


class PedidoVendaSerializer(BancoContextMixin, serializers.ModelSerializer):
    valor_total = serializers.FloatField(source='pedi_tota', read_only=True)
    valor_subtotal = serializers.FloatField(source='pedi_topr', read_only=True)
    valor_desconto = serializers.FloatField(source='pedi_desc', read_only=True)
    cliente_nome = serializers.SerializerMethodField(read_only=True)
    empresa_nome = serializers.SerializerMethodField(read_only=True)
    itens = serializers.SerializerMethodField()
    itens_input = ItemPedidoVendaSerializer(many=True, write_only=True, required=False)
    pedi_nume = serializers.IntegerField(read_only=True)
    parametros = serializers.DictField(write_only=True, required=False)
    gerar_titulos = serializers.BooleanField(write_only=True, required=False, default=False)
    financeiro_titulos = serializers.DictField(write_only=True, required=False)

    class Meta:
        model = PedidoVenda
        fields = [
            'pedi_empr', 'pedi_fili', 'pedi_data', 'pedi_tota', 'pedi_topr', 'pedi_forn', 'pedi_form_rece',
            'itens', 'itens_input', 'parametros', 'pedi_desc', 'pedi_obse', 'pedi_fina', 'pedi_liqu',
            'valor_total', 'valor_subtotal', 'valor_desconto', 'cliente_nome', 'empresa_nome', 'pedi_nume', 'pedi_stat', 'pedi_vend',
            'gerar_titulos', 'financeiro_titulos'
        ]

    def get_itens(self, obj):
        banco = self.context.get('banco')
        itens = Itenspedidovenda.objects.using(banco).filter(
            iped_empr=obj.pedi_empr,
            iped_fili=obj.pedi_fili,
            iped_pedi=str(obj.pedi_nume)
        )
        return ItemPedidoVendaSerializer(itens, many=True, context=self.context).data

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        itens_data = validated_data.pop('itens_input', None)
        if not itens_data:
            itens_data = validated_data.pop('itens', [])

        parametros = validated_data.pop('parametros', {})
        usar_desconto_item = parametros.get('usar_desconto_item', False)
        usar_desconto_total = parametros.get('usar_desconto_total', False)

        gerar_titulos = validated_data.pop('gerar_titulos', False)
        financeiro_titulos = validated_data.pop('financeiro_titulos', {})

        if usar_desconto_item and usar_desconto_total:
            raise ValidationError("Não é possível aplicar desconto por item e desconto no total simultaneamente.")

        if not itens_data:
            raise ValidationError("Itens do pedido são obrigatórios.")

        valores = calcular_valores_pedido(
            itens_data,
            desconto_total=validated_data.get('pedi_desc'),
            desconto_percentual=parametros.get('desconto_percentual')
        )
        liquido = valores['total'] - valores['desconto']
        validated_data['pedi_topr'] = valores['subtotal']
        validated_data['pedi_desc'] = valores['desconto']
        validated_data['pedi_tota'] = valores['total']
        validated_data['pedi_liqu'] = liquido
        validated_data['pedi_fina'] = validated_data.get('pedi_fina', '0')

        if 'pedi_form_rece' not in validated_data or validated_data['pedi_form_rece'] is None:
            validated_data['pedi_form_rece'] = '54'

        pedidos_existente = None
        if 'pedi_nume' in validated_data:
            pedidos_existente = PedidoVenda.objects.using(banco).filter(
                pedi_empr=validated_data['pedi_empr'],
                pedi_fili=validated_data['pedi_fili'],
                pedi_nume=validated_data['pedi_nume'],
            ).first()

        if pedidos_existente:
            Itenspedidovenda.objects.using(banco).filter(
                iped_empr=pedidos_existente.pedi_empr,
                iped_fili=pedidos_existente.pedi_fili,
                iped_pedi=str(pedidos_existente.pedi_nume)
            ).delete()

            for attr, value in validated_data.items():
                setattr(pedidos_existente, attr, value)
            pedidos_existente.save(using=banco)
            pedido = pedidos_existente
        else:
            ultimo = PedidoVenda.objects.using(banco).filter(
                pedi_empr=validated_data['pedi_empr'],
                pedi_fili=validated_data['pedi_fili']
            ).order_by('-pedi_nume').first()
            validated_data['pedi_nume'] = (ultimo.pedi_nume + 1) if ultimo else 1

            pedido = PedidoVenda.objects.using(banco).create(**validated_data)

        itens_criados = []
        for idx, item_data in enumerate(itens_data, start=1):
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

            item = Itenspedidovenda.objects.using(banco).create(
                iped_empr=pedido.pedi_empr,
                iped_fili=pedido.pedi_fili,
                iped_item=idx,
                iped_pedi=str(pedido.pedi_nume),
                iped_data=pedido.pedi_data,
                iped_forn=pedido.pedi_forn,
                iped_vend=pedido.pedi_vend,
                iped_unli=subtotal_bruto,
                iped_suto=subtotal_bruto,
                iped_tota=total_item,
                **item_data_clean
            )
            itens_criados.append(item)

        if usar_desconto_item or usar_desconto_total:
            try:
                aplicar_descontos(pedido, itens_criados, usar_desconto_item, usar_desconto_total)
            except Exception as e:
                logger.error(f"Erro ao aplicar descontos: {e}")

        if usar_desconto_item or usar_desconto_total:
            pedido.save(using=banco)

        try:
            resultado_estoque = PedidosService.baixa_estoque_pedido(
                pedido, itens_data, self.context.get('request')
            )
            if not resultado_estoque.get('sucesso', True):
                logger.warning(f"Erro ao processar estoque: {resultado_estoque.get('erro')}")
        except Exception as e:
            logger.error(f"Erro ao processar saída de estoque: {e}")

        if gerar_titulos and pedido.pedi_fina == '1':
            try:
                from rest_framework.test import APIRequestFactory
                titulos_data = {
                    'pedi_nume': pedido.pedi_nume,
                    'pedi_forn': pedido.pedi_forn,
                    'pedi_tota': str(pedido.pedi_tota),
                    'forma_pagamento': financeiro_titulos.get('forma_pagamento', ''),
                    'parcelas': financeiro_titulos.get('parcelas', 1),
                    'data_base': financeiro_titulos.get('data_base', datetime.now().date().isoformat())
                }
                factory = APIRequestFactory()
                request = factory.post('/gerar-titulos-pedido/', titulos_data, format='json')
                request.data = titulos_data
                from core.registry import get_licenca_db_config
                request.licenca_slug = self.context.get('request').licenca_slug if self.context.get('request') else None
                view = GerarTitulosPedidoView()
                view.request = request
                view.post(request)
            except Exception as e:
                logger.error(f"Erro ao gerar títulos para pedido {pedido.pedi_nume}: {e}")

        return pedido

    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        itens_data = validated_data.pop('itens_input', None)
        if itens_data is None:
            itens_data = validated_data.pop('itens', None)

        parametros = validated_data.pop('parametros', {})
        usar_desconto_item = parametros.get('usar_desconto_item', False)
        usar_desconto_total = parametros.get('usar_desconto_total', False)

        gerar_titulos = validated_data.pop('gerar_titulos', False)
        financeiro_titulos = validated_data.pop('financeiro_titulos', {})

        if usar_desconto_item and usar_desconto_total:
            raise ValidationError("Não é possível aplicar desconto por item e desconto no total simultaneamente.")

        if itens_data is None:
            raise ValidationError("Itens do pedido são obrigatórios.")

        valores = calcular_valores_pedido(
            itens_data,
            desconto_total=validated_data.get('pedi_desc'),
            desconto_percentual=parametros.get('desconto_percentual')
        )
        liquido = valores['total'] - valores['desconto']
        validated_data['pedi_topr'] = valores['subtotal']
        validated_data['pedi_desc'] = valores['desconto']
        validated_data['pedi_tota'] = valores['total']
        validated_data['pedi_liqu'] = liquido
        validated_data['pedi_fina'] = validated_data.get('pedi_fina', '0')

        if 'pedi_form_rece' not in validated_data or validated_data['pedi_form_rece'] is None:
            validated_data['pedi_form_rece'] = '54'

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)

        Itenspedidovenda.objects.using(banco).filter(
            iped_empr=instance.pedi_empr,
            iped_fili=instance.pedi_fili,
            iped_pedi=str(instance.pedi_nume)
        ).delete()

        itens_criados = []
        for idx, item_data in enumerate(itens_data, start=1):
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

            item = Itenspedidovenda.objects.using(banco).create(
                iped_empr=instance.pedi_empr,
                iped_fili=instance.pedi_fili,
                iped_item=idx,
                iped_pedi=str(instance.pedi_nume),
                iped_data=instance.pedi_data,
                iped_forn=instance.pedi_forn,
                iped_vend=instance.pedi_vend,
                iped_unli=subtotal_bruto,
                iped_suto=subtotal_bruto,
                iped_tota=total_item,
                **item_data_clean
            )
            itens_criados.append(item)

        if usar_desconto_item or usar_desconto_total:
            try:
                aplicar_descontos(instance, itens_criados, usar_desconto_item, usar_desconto_total)
            except Exception as e:
                logger.error(f"Erro ao aplicar descontos na atualização: {e}")

        if usar_desconto_item or usar_desconto_total:
            instance.save(using=banco)

        try:
            resultado_estoque = PedidosService.baixa_estoque_pedido(
                instance, itens_data, self.context.get('request')
            )
            if not resultado_estoque.get('sucesso', True):
                logger.warning(f"Erro ao processar estoque: {resultado_estoque.get('erro')}")
        except Exception as e:
            logger.error(f"Erro ao processar saída de estoque: {e}")

        if gerar_titulos and instance.pedi_fina == '1':
            try:
                from rest_framework.test import APIRequestFactory
                titulos_data = {
                    'pedi_nume': instance.pedi_nume,
                    'pedi_forn': instance.pedi_forn,
                    'pedi_tota': str(instance.pedi_tota),
                    'forma_pagamento': financeiro_titulos.get('forma_pagamento', ''),
                    'parcelas': financeiro_titulos.get('parcelas', 1),
                    'data_base': financeiro_titulos.get('data_base', datetime.now().date().isoformat())
                }
                factory = APIRequestFactory()
                request = factory.post('/gerar-titulos-pedido/', titulos_data, format='json')
                request.data = titulos_data
                from core.registry import get_licenca_db_config
                request.licenca_slug = self.context.get('request').licenca_slug if self.context.get('request') else None
                view = GerarTitulosPedidoView()
                view.request = request
                view.post(request)
            except Exception as e:
                logger.error(f"Erro ao gerar títulos na atualização do pedido {instance.pedi_nume}: {e}")

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
            entidades = Entidades.objects.using(banco).filter(
                enti_clie=obj.pedi_forn,
                enti_empr=obj.pedi_empr,
            ).first()
            return entidades.enti_nome if entidades else None
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
            empresa = Empresas.objects.using(banco).filter(empr_codi=obj.pedi_empr).first()
            return empresa.empr_nome if empresa else None
        except Exception as e:
            logger.warning(f"Erro ao buscar empresa: {e}")
            return None

class PedidosGeralSerializer(serializers.ModelSerializer):
    class Meta:
        model = PedidosGeral
        fields = '__all__'