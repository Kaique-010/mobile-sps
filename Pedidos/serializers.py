from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from Licencas.models import Empresas
from Produtos.models import Produtos
from .models import PedidoVenda, Itenspedidovenda
from Entidades.models import Entidades
from core.serializers import BancoContextMixin
from parametros_admin.integracao_pedidos import processar_saida_estoque_pedido
from parametros_admin.utils_pedidos import aplicar_descontos
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
    cliente_nome = serializers.SerializerMethodField(read_only=True)
    empresa_nome = serializers.SerializerMethodField(read_only=True)
    itens = serializers.SerializerMethodField()  # Mudança aqui - remover write_only
    itens_input = ItemPedidoVendaSerializer(many=True, write_only=True, required=False)
    pedi_nume = serializers.IntegerField(read_only=True)  # Resolve a pk sendo o numero pois ele retorna sequencial na mão 
    parametros = serializers.DictField(write_only=True, required=False)  # Para receber parâmetros de desconto

    class Meta:
        model = PedidoVenda
        fields = [
            'pedi_empr', 'pedi_fili', 'pedi_data', 'pedi_tota', 'pedi_forn',
            'itens', 'itens_input', 'parametros',
            'valor_total', 'cliente_nome', 'empresa_nome', 'pedi_nume', 'pedi_stat', 'pedi_vend'
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
        print(f"🆕 [PEDIDO] Iniciando criação de pedido")
        print(f"🆕 [PEDIDO] Dados validados: {validated_data}")
        
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        # Aceitar tanto 'itens_input' quanto 'itens'
        itens_data = validated_data.pop('itens_input', None)
        if not itens_data:
            itens_data = validated_data.pop('itens', [])
        
        # Extrair parâmetros de desconto
        parametros = validated_data.pop('parametros', {})
        usar_desconto_item = parametros.get('usar_desconto_item', False)
        usar_desconto_total = parametros.get('usar_desconto_total', False)
        
        # Validação para impedir aplicação simultânea de desconto por item e por pedido
        if usar_desconto_item and usar_desconto_total:
            raise ValidationError("Não é possível aplicar desconto por item e desconto no total simultaneamente.")
        
        print(f"🆕 [PEDIDO] Quantidade de itens recebidos: {len(itens_data)}")
        print(f"🆕 [PEDIDO] Parâmetros de desconto: usar_item={usar_desconto_item}, usar_total={usar_desconto_total}")
        
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

        # Criar itens do pedido
        itens_criados = []
        total = 0
        for idx, item_data in enumerate(itens_data, start=1):
            item = Itenspedidovenda.objects.using(banco).create(
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
            itens_criados.append(item)
            total += item_data.get('iped_quan', 0) * item_data.get('iped_unit', 0)

        pedido.pedi_tota = total
        pedido.save(using=banco)

        # Aplicar descontos se configurado
        if usar_desconto_item or usar_desconto_total:
            print(f"🆕 [PEDIDO] Aplicando descontos no pedido {pedido.pedi_nume}")
            try:
                aplicar_descontos(pedido, itens_criados, usar_desconto_item, usar_desconto_total)
                print(f"✅ [PEDIDO] Descontos aplicados com sucesso")
            except Exception as e:
                print(f"❌ [PEDIDO] Erro ao aplicar descontos: {e}")
                logger.error(f"Erro ao aplicar descontos: {e}")

        # Processar saída de estoque se configurado
        print(f"🔄 [PEDIDO] Iniciando processamento de estoque para pedido {pedido.pedi_nume}")
        try:
            resultado_estoque = processar_saida_estoque_pedido(
                pedido, itens_data, self.context.get('request')
            )
            print(f"🔄 [PEDIDO] Resultado do processamento de estoque: {resultado_estoque}")
            
            if not resultado_estoque.get('sucesso', True):
                print(f"❌ [PEDIDO] ERRO ao processar estoque: {resultado_estoque.get('erro')}")
                logger.warning(f"Erro ao processar estoque: {resultado_estoque.get('erro')}")
            elif resultado_estoque.get('processado'):
                print(f"✅ [PEDIDO] Estoque processado com SUCESSO para pedido {pedido.pedi_nume}")
                logger.info(f"Estoque processado para pedido {pedido.pedi_nume}")
            else:
                print(f"⚠️ [PEDIDO] Estoque NÃO foi processado: {resultado_estoque.get('motivo', 'Motivo não informado')}")
        except Exception as e:
            print(f"💥 [PEDIDO] EXCEÇÃO ao processar saída de estoque: {e}")
            logger.error(f"Erro ao processar saída de estoque: {e}")

        return pedido


    def update(self, instance, validated_data):
        print(f"🔄 [PEDIDO] Iniciando atualização de pedido {instance.pedi_nume}")
        print(f"🔄 [PEDIDO] Dados validados: {validated_data}")
        
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        # Aceitar tanto 'itens_input' quanto 'itens'
        itens_data = validated_data.pop('itens_input', None)
        if itens_data is None:
            itens_data = validated_data.pop('itens', None)
        
        # Extrair parâmetros de desconto
        parametros = validated_data.pop('parametros', {})
        usar_desconto_item = parametros.get('usar_desconto_item', False)
        usar_desconto_total = parametros.get('usar_desconto_total', False)
        
        # Validação para impedir aplicação simultânea de desconto por item e por pedido
        if usar_desconto_item and usar_desconto_total:
            raise ValidationError("Não é possível aplicar desconto por item e desconto no total simultaneamente.")
        
        print(f"🔄 [PEDIDO] Parâmetros de desconto: usar_item={usar_desconto_item}, usar_total={usar_desconto_total}")
        
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
        itens_criados = []
        total = 0
        for idx, item_data in enumerate(itens_data, start=1):
            item = Itenspedidovenda.objects.using(banco).create(
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
            itens_criados.append(item)
            total += item_data.get('iped_quan', 0) * item_data.get('iped_unit', 0)

        instance.pedi_tota = total
        instance.save(using=banco)

        # Aplicar descontos se configurado
        if usar_desconto_item or usar_desconto_total:
            print(f"🔄 [PEDIDO] Aplicando descontos na atualização do pedido {instance.pedi_nume}")
            try:
                aplicar_descontos(instance, itens_criados, usar_desconto_item, usar_desconto_total)
                print(f"✅ [PEDIDO] Descontos aplicados com sucesso na atualização")
            except Exception as e:
                print(f"❌ [PEDIDO] Erro ao aplicar descontos na atualização: {e}")
                logger.error(f"Erro ao aplicar descontos na atualização: {e}")

        # Processar saída de estoque se configurado
        print(f"🔄 [PEDIDO] Iniciando processamento de estoque para atualização do pedido {instance.pedi_nume}")
        try:
            resultado_estoque = processar_saida_estoque_pedido(
                instance, itens_data, self.context.get('request')
            )
            print(f"🔄 [PEDIDO] Resultado do processamento de estoque: {resultado_estoque}")
            
            if not resultado_estoque.get('sucesso', True):
                print(f"❌ [PEDIDO] ERRO ao processar estoque: {resultado_estoque.get('erro')}")
                logger.warning(f"Erro ao processar estoque: {resultado_estoque.get('erro')}")
            elif resultado_estoque.get('processado'):
                print(f"✅ [PEDIDO] Estoque processado com SUCESSO para pedido {instance.pedi_nume}")
                logger.info(f"Estoque processado para pedido {instance.pedi_nume}")
            else:
                print(f"⚠️ [PEDIDO] Estoque NÃO foi processado: {resultado_estoque.get('motivo', 'Motivo não informado')}")
        except Exception as e:
            print(f"💥 [PEDIDO] EXCEÇÃO ao processar saída de estoque: {e}")
            logger.error(f"Erro ao processar saída de estoque: {e}")

        return instance

 
    

    

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
            entidades = Entidades.objects.using(banco).filter(
                enti_clie=obj.pedi_forn,
                enti_empr=obj.pedi_empr,
            ).first()

            return entidades.enti_nome if entidades else None

        except Exception as e:
            logger.warning(f"Erro ao buscar cliente: {e}")
            return None
    
    
    def get_empresa_nome(self, obj):
        # Tentar usar cache primeiro
        empresas_cache = self.context.get('empresas_cache')
        if empresas_cache:
            return empresas_cache.get(obj.pedi_empr)
        
        # Fallback para consulta individual
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            empresa = Empresas.objects.using(banco).filter(empr_codi=obj.pedi_empr).first()
            return empresa.empr_nome if empresa else None
        except Exception as e:
            logger.warning(f"Erro ao buscar empresa: {e}")
            return None
    
    
from .models import PedidosGeral

class PedidosGeralSerializer(serializers.ModelSerializer):
    class Meta:
        model = PedidosGeral
        fields = '__all__'
