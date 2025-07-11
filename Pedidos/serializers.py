from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from Licencas.models import Empresas
from Produtos.models import Produtos
from .models import PedidoVenda, Itenspedidovenda
from Entidades.models import Entidades
from core.serializers import BancoContextMixin
from parametros_admin.integracao_pedidos import processar_saida_estoque_pedido
import logging

logger = logging.getLogger(__name__)


class ItemPedidoVendaSerializer(BancoContextMixin,serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField()
    class Meta:
        model = Itenspedidovenda
        exclude = ['iped_empr', 'iped_fili', 'iped_item', 'iped_pedi', 'iped_data', 'iped_forn', 'iped_vend', 'iped_suto']
    
    
    def get_produto_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            logger.warning("Banco não informado no context.")
            return None
        try:
            produto = Produtos.objects.using(banco).get(prod_codi=obj.iped_prod)
            return produto.prod_nome
        except Exception as e:
            logger.error(f"Erro ao buscar produto: {e}")
            return None

            
            
class PedidoVendaSerializer(BancoContextMixin, serializers.ModelSerializer):
    valor_total = serializers.FloatField(source='pedi_tota', read_only=True)
    cliente_nome = serializers.SerializerMethodField(read_only=True)
    empresa_nome = serializers.SerializerMethodField(read_only=True)
    itens = serializers.SerializerMethodField()
    itens_input = ItemPedidoVendaSerializer(many=True, write_only=True, required=True)
    pedi_nume = serializers.IntegerField(read_only=True)  # Resolve a pk sendo o numero pois ele retorna sequencial na mão 

    class Meta:
        model = PedidoVenda
        fields = [
            'pedi_empr', 'pedi_fili', 'pedi_data', 'pedi_tota', 'pedi_forn',
            'itens', 'itens_input',
            'valor_total', 'cliente_nome', 'empresa_nome', 'pedi_nume', 'pedi_stat'
        ]
    
    def get_itens(self, obj):
        banco = self.context.get('banco')
        itens = Itenspedidovenda.objects.using(banco).filter(
            iped_empr=obj.pedi_empr,
            iped_fili=obj.pedi_fili,
            iped_pedi=str(obj.pedi_nume)
        )
        return ItemPedidoVendaSerializer(itens, many=True, context=self.context).data


    #metodo de criacao de pedidos ja olhando se era um pedido criado ou não no update
    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        itens_data = validated_data.pop('itens_input', [])
        if not itens_data:
            raise ValidationError("Itens do pedido são obrigatórios.")

        pedidos_existente = None
        if 'pedi_nume' in validated_data:
            pedidos_existente = PedidoVenda.objects.using(banco).filter(
                pedi_empr=validated_data['pedi_empr'],
                pedi_fili=validated_data['pedi_fili'],
                pedi_nume=validated_data['pedi_nume'],
            ).first()

        if pedidos_existente:
            # edição disfarçada
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

        total = 0
        for idx, item_data in enumerate(itens_data, start=1):
            Itenspedidovenda.objects.using(banco).create(
                iped_empr=pedido.pedi_empr,
                iped_fili=pedido.pedi_fili,
                iped_item=idx,
                iped_pedi=str(pedido.pedi_nume),
                iped_data=pedido.pedi_data,
                iped_forn=pedido.pedi_forn,
                iped_vend=pedido.pedi_vend,
                iped_suto=pedido.pedi_tota,
                **item_data
            )
            total += item_data.get('iped_quan', 0) * item_data.get('iped_unit', 0)

        pedido.pedi_tota = total
        pedido.save(using=banco)

        # Processar saída de estoque se configurado
        try:
            resultado_estoque = processar_saida_estoque_pedido(
                pedido, itens_data, self.context.get('request')
            )
            if not resultado_estoque.get('sucesso', True):
                logger.warning(f"Erro ao processar estoque: {resultado_estoque.get('erro')}")
            elif resultado_estoque.get('processado'):
                logger.info(f"Estoque processado para pedido {pedido.pedi_nume}")
        except Exception as e:
            logger.error(f"Erro ao processar saída de estoque: {e}")

        return pedido


    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        itens_data = validated_data.pop('itens_input', None)
        if itens_data is None:
            raise ValidationError("Itens do pedido são obrigatórios.")

        # Atualiza campos do pedido
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)

        # Remove todos os itens antigos do pedido
        Itenspedidovenda.objects.using(banco).filter(
            iped_empr=instance.pedi_empr,
            iped_fili=instance.pedi_fili,
            iped_pedi=str(instance.pedi_nume)
        ).delete()

        # Recria os itens
        total = 0
        for idx, item_data in enumerate(itens_data, start=1):
            Itenspedidovenda.objects.using(banco).create(
                iped_empr=instance.pedi_empr,
                iped_fili=instance.pedi_fili,
                iped_item=idx,
                iped_pedi=str(instance.pedi_nume),
                iped_data=instance.pedi_data,
                iped_forn=instance.pedi_forn,
                iped_vend=instance.pedi_vend,
                iped_suto=instance.pedi_tota,
                **item_data
            )
            total += item_data.get('iped_quan', 0) * item_data.get('iped_unit', 0)

        instance.pedi_tota = total
        instance.save(using=banco)

        # Processar saída de estoque se configurado
        try:
            resultado_estoque = processar_saida_estoque_pedido(
                instance, itens_data, self.context.get('request')
            )
            if not resultado_estoque.get('sucesso', True):
                logger.warning(f"Erro ao processar estoque: {resultado_estoque.get('erro')}")
            elif resultado_estoque.get('processado'):
                logger.info(f"Estoque processado para pedido {instance.pedi_nume}")
        except Exception as e:
            logger.error(f"Erro ao processar saída de estoque: {e}")

        return instance

 
    

    

    def get_cliente_nome(self, obj):
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
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            return Empresas.objects.using(banco).get(empr_codi=obj.pedi_empr).empr_nome
        except Empresas.DoesNotExist:
            logger.warning(f"Empresa com ID {obj.pedi_empr} não encontrada.")
            return None

    def get_produto_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None
        try:
            produto = Produtos.objects.using(banco).filter(
                prod_codi=obj.iped_prod,
                prod_empr=obj.iped_empr
            ).first()
            return produto.prod_nome if produto else None
        except Exception as e:
            logger.warning(f"Erro ao buscar nome do produto: {e}")
            return None
    
    
    
from .models import PedidosGeral

class PedidosGeralSerializer(serializers.ModelSerializer):
    class Meta:
        model = PedidosGeral
        fields = '__all__'
