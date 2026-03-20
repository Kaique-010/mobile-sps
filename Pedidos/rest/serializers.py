from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from datetime import datetime
from Licencas.models import Empresas
from Produtos.models import Produtos
from ..models import PedidoVenda, Itenspedidovenda, PedidosGeral
from Entidades.models import Entidades
from core.serializers import BancoContextMixin
from core.utils import calcular_valores_pedido
from ..services.pedido_service import PedidoVendaService
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

        validated_data['pedi_fina'] = validated_data.get('pedi_fina', '0')

        if 'pedi_form_rece' not in validated_data or validated_data['pedi_form_rece'] is None:
            validated_data['pedi_form_rece'] = '54'

        if validated_data.get('pedi_desc') is None and parametros.get('desconto_percentual') is not None:
            valores = calcular_valores_pedido(itens_data, desconto_percentual=parametros.get('desconto_percentual'))
            validated_data['pedi_desc'] = valores['desconto']

        request = self.context.get('request')
        pedido = PedidoVendaService.create_pedido_venda(
            banco=banco,
            pedido_data=validated_data,
            itens_data=itens_data,
            pedi_tipo_oper=parametros.get('tipo_oper') or 'VENDA',
            request=request,
        )

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

        validated_data['pedi_fina'] = validated_data.get('pedi_fina', '0')

        if 'pedi_form_rece' not in validated_data or validated_data['pedi_form_rece'] is None:
            validated_data['pedi_form_rece'] = '54'

        if validated_data.get('pedi_desc') is None and parametros.get('desconto_percentual') is not None:
            valores = calcular_valores_pedido(itens_data, desconto_percentual=parametros.get('desconto_percentual'))
            validated_data['pedi_desc'] = valores['desconto']

        request = self.context.get('request')
        instance = PedidoVendaService.update_pedido_venda(
            banco=banco,
            pedido=instance,
            pedido_updates=validated_data,
            itens_data=itens_data,
            pedi_tipo_oper=parametros.get('tipo_oper') or 'VENDA',
            request=request,
        )

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
