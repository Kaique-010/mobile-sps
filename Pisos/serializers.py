from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from core.serializers import BancoContextMixin
from .models import Orcamentopisos, Itensorcapisos, Itenspedidospisos, Pedidospisos   
from Licencas.models import Empresas
from Produtos.models import Produtos   
from Entidades.models import Entidades
import logging

logger = logging.getLogger(__name__)    



class ItensorcapisosSerializer(serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField()
    class Meta:
        model = Itensorcapisos
        fields = '__all__'
    
    def get_produto_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            logger.warning("Banco não informado no context.")
            return None
        try:
            produto = Produtos.objects.using(banco).filter(
                prod_codi=obj.item_prod,
                prod_empr=obj.item_empr
            ).first()
            return produto.prod_nome if produto else None
        except Exception as e:
            logger.error(f"Erro ao buscar produto: {e}")
            return None



class OrcamentopisosSerializer(BancoContextMixin, serializers.ModelSerializer):
    cliente_nome = serializers.SerializerMethodField()
    empresa_nome = serializers.SerializerMethodField()
    itens = serializers.SerializerMethodField(read_only=True)
    itens_input = ItensorcapisosSerializer(many=True, write_only=True, required=False)
    
    class Meta:
        model = Orcamentopisos
        fields = '__all__'

    def get_itens(self, obj):
        banco = self.context.get('banco')
        itens = Itensorcapisos.objects.using(banco).filter(
            item_empr=obj.orca_empr,
            item_fili=obj.orca_fili,
            item_orca=obj.orca_nume
        )
        return ItensorcapisosSerializer(itens, many=True, context=self.context).data

    
    def get_cliente_nome(self, obj):
        # Primeiro tentar usar o cache do contexto
        entidades_cache = self.context.get('entidades_cache')
        if entidades_cache:
            cache_key = f"{obj.orca_clie}_{obj.orca_empr}"
            return entidades_cache.get(cache_key)
        
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            entidades = Entidades.objects.using(banco).filter(
                enti_clie=obj.orca_clie,
                enti_empr=obj.orca_empr,
            ).first()

            return entidades.enti_nome if entidades else None

        except Exception as e:
            logger.warning(f"Erro ao buscar cliente: {e}")
            return None
    
    
    def get_empresa_nome(self, obj):
        # Tentar usar cache primeiro
        empresas_cache = self.context.get('empresas_cache')
        if empresas_cache:
            return empresas_cache.get(obj.orca_empr)
        
        # Fallback para consulta individual
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            empresa = Empresas.objects.using(banco).filter(empr_codi=obj.orca_empr).first()
            return empresa.empr_nome if empresa else None
        except Exception as e:
            logger.warning(f"Erro ao buscar empresa: {e}")
            return None

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        # Extrair itens e parâmetros
        itens_data = validated_data.pop('itens_input', [])
        
        if not itens_data:
            raise ValidationError("Itens do orçamento são obrigatórios.")

        # Calcular valores totais
        subtotal = sum(
            float(item.get('item_quan', 0)) * float(item.get('item_unit', 0))
            for item in itens_data
        )
        desconto = sum(float(item.get('item_desc', 0)) for item in itens_data)
        total = subtotal - desconto
        
        validated_data['orca_tota'] = total
        validated_data['orca_desc'] = desconto

        # Verificar se orçamento já existe
        orcamento_existente = None
        if 'orca_nume' in validated_data:
            orcamento_existente = Orcamentopisos.objects.using(banco).filter(
                orca_empr=validated_data['orca_empr'],
                orca_fili=validated_data['orca_fili'],
                orca_nume=validated_data['orca_nume']
            ).first()

        if orcamento_existente:
            # Atualizar orçamento existente
            Itensorcapisos.objects.using(banco).filter(
                item_empr=orcamento_existente.orca_empr,
                item_fili=orcamento_existente.orca_fili,
                item_orca=orcamento_existente.orca_nume
            ).delete()

            for attr, value in validated_data.items():
                setattr(orcamento_existente, attr, value)
            orcamento_existente.save(using=banco)
            orcamento = orcamento_existente
        else:
            # Criar novo orçamento
            ultimo = Orcamentopisos.objects.using(banco).filter(
                orca_empr=validated_data['orca_empr'],
                orca_fili=validated_data['orca_fili']
            ).order_by('-orca_nume').first()
            validated_data['orca_nume'] = (ultimo.orca_nume + 1) if ultimo else 1

            orcamento = Orcamentopisos.objects.using(banco).create(**validated_data)

        # Criar itens do orçamento
        for idx, item_data in enumerate(itens_data, start=1):
            # Calcular subtotal do item
            item_subtotal = float(item_data.get('item_quan', 0)) * float(item_data.get('item_unit', 0))

            item_data_clean = item_data.copy()
            item_data_clean.pop('item_suto', None)

            # Mapear campos específicos se necessário
            if 'area_m2' in item_data_clean:
                item_data_clean['item_m2'] = item_data_clean.pop('area_m2')
            if 'observacoes' in item_data_clean:
                item_data_clean['item_obse'] = item_data_clean.pop('observacoes')

            # Criar item de orçamento corretamente
            Itensorcapisos.objects.using(banco).create(
                item_empr=orcamento.orca_empr,
                item_fili=orcamento.orca_fili,
                item_orca=orcamento.orca_nume,
                item_ambi=item_data.get('item_ambi', idx),
                item_nume=idx,
                item_suto=item_subtotal,
                **item_data_clean
            )

        return orcamento

    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        # Extrair itens e parâmetros
        itens_data = validated_data.pop('itens_input', [])
        
        if not itens_data:
            raise ValidationError("Itens do orçamento são obrigatórios.")

        # Calcular valores totais
        subtotal = sum(
            float(item.get('item_quan', 0)) * float(item.get('item_unit', 0))
            for item in itens_data
        )
        desconto = sum(float(item.get('item_desc', 0)) for item in itens_data)
        total = subtotal - desconto

        # Atualizar dados do orçamento
        instance.orca_tota = total
        instance.orca_desc = desconto
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)

        # Remover itens antigos
        Itensorcapisos.objects.using(banco).filter(
            item_empr=instance.orca_empr,
            item_fili=instance.orca_fili,
            item_orca=instance.orca_nume
        ).delete()

        # Recriar itens
        for idx, item_data in enumerate(itens_data, start=1):
            item_subtotal = float(item_data.get('item_quan', 0)) * float(item_data.get('item_unit', 0))

            item_data_clean = item_data.copy()
            item_data_clean.pop('item_suto', None)

            # Mapear campos específicos
            if 'area_m2' in item_data_clean:
                item_data_clean['item_m2'] = item_data_clean.pop('area_m2')
            if 'observacoes' in item_data_clean:
                item_data_clean['item_obse'] = item_data_clean.pop('observacoes')

            Itensorcapisos.objects.using(banco).create(
                item_empr=instance.orca_empr,
                item_fili=instance.orca_fili,
                item_orca=instance.orca_nume,
                item_ambi=item_data.get('item_ambi', idx),
                item_nume=idx,
                item_suto=item_subtotal,
                **item_data_clean
            )

        return instance

class ItenspedidospisosSerializer(BancoContextMixin, serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField()
    item_nume = serializers.IntegerField(read_only=True)  # Sequencial criado pelo backend
    
    class Meta:
        model = Itenspedidospisos
        fields = '__all__'
    
    def get_produto_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            logger.warning("Banco não informado no context.")
            return None
        try:
            produto = Produtos.objects.using(banco).filter(
                prod_codi=obj.item_prod,
                prod_empr=obj.item_empr
            ).first()
            return produto.prod_nome if produto else None
        except Exception as e:
            logger.error(f"Erro ao buscar produto: {e}")
            return None
    



class PedidospisosSerializer(BancoContextMixin, serializers.ModelSerializer):
    cliente_nome = serializers.SerializerMethodField()
    empresa_nome = serializers.SerializerMethodField()
    itens = serializers.SerializerMethodField(read_only=True)
    itens_input = ItenspedidospisosSerializer(many=True, write_only=True, required=False)
    parametros = serializers.DictField(write_only=True, required=False)
    pedi_nume = serializers.IntegerField(read_only=True)  
    
    class Meta:
        model = Pedidospisos
        fields = '__all__'

    def get_itens(self, obj):
        banco = self.context.get('banco')
        itens = Itenspedidospisos.objects.using(banco).filter(
            item_empr=obj.pedi_empr,
            item_fili=obj.pedi_fili,
            item_pedi=str(obj.pedi_nume)
        )
        return ItenspedidospisosSerializer(itens, many=True, context=self.context).data

    
    def get_cliente_nome(self, obj):
        # Primeiro tentar usar o cache do contexto
        entidades_cache = self.context.get('entidades_cache')
        if entidades_cache:
            cache_key = f"{obj.pedi_clie}_{obj.pedi_empr}"
            return entidades_cache.get(cache_key)
        
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            entidades = Entidades.objects.using(banco).filter(
                enti_clie=obj.pedi_clie,
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

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        # Extrair itens e parâmetros
        itens_data = validated_data.pop('itens_input', [])
        
        if not itens_data:
            raise ValidationError("Itens do pedido são obrigatórios.")

        # Converter campos para string se necessário
        if 'pedi_ajus_port' in validated_data and validated_data['pedi_ajus_port'] is not None:
            validated_data['pedi_ajus_port'] = str(validated_data['pedi_ajus_port'])
        if 'pedi_degr_esca' in validated_data and validated_data['pedi_degr_esca'] is not None:
            validated_data['pedi_degr_esca'] = str(validated_data['pedi_degr_esca'])

        # Normalizar campos dos itens
        # Normalizar campos dos itens
        for item in itens_data:
            # Mapear campos iped_* para item_*
            if 'iped_prod' in item and 'item_prod' not in item:
                item['item_prod'] = item.pop('iped_prod')
            if 'iped_quan' in item and 'item_quan' not in item:
                item['item_quan'] = item.pop('iped_quan')
            if 'iped_unit' in item and 'item_unit' not in item:
                item['item_unit'] = item.pop('iped_unit')
            if 'iped_tota' in item and 'item_tota' not in item:
                item['item_tota'] = item.pop('iped_tota')
            
            # Mapear campos adicionais
            if 'area_m2' in item and 'item_m2' not in item:
                item['item_m2'] = item.pop('area_m2')
            if 'observacoes' in item and 'item_obse' not in item:
                item['item_obse'] = item.pop('observacoes')
            
            # Garantir campo obrigatório item_ambi
            if 'item_ambi' not in item:
                item['item_ambi'] = 1  # Valor padrão

        # Calcular valores totais
        subtotal = sum(
            float(item.get('item_quan', 0)) * float(item.get('item_unit', 0))
            for item in itens_data
        )
        desconto = sum(float(item.get('item_desc', 0)) for item in itens_data)
        total = subtotal - desconto
        
        validated_data['pedi_tota'] = total
        validated_data['pedi_desc'] = desconto

        # Verificar se pedido já existe
        pedido_existente = None
        if 'pedi_nume' in validated_data:
            pedido_existente = Pedidospisos.objects.using(banco).filter(
                pedi_empr=validated_data['pedi_empr'],
                pedi_fili=validated_data['pedi_fili'],
                pedi_nume=validated_data['pedi_nume']
            ).first()

        if pedido_existente:
            # Atualizar pedido existente
            Itenspedidospisos.objects.using(banco).filter(
                item_empr=pedido_existente.pedi_empr,
                item_fili=pedido_existente.pedi_fili,
                item_pedi=pedido_existente.pedi_nume
            ).delete()

            for attr, value in validated_data.items():
                setattr(pedido_existente, attr, value)
            pedido_existente.save(using=banco)
            pedido = pedido_existente
        else:
            # Criar novo pedido
            ultimo = Pedidospisos.objects.using(banco).filter(
                pedi_empr=validated_data['pedi_empr'],
                pedi_fili=validated_data['pedi_fili']
            ).order_by('-pedi_nume').first()
            validated_data['pedi_nume'] = (ultimo.pedi_nume + 1) if ultimo else 1

            pedido = Pedidospisos.objects.using(banco).create(**validated_data)

        # Criar itens do pedido
        # Recriar itens
        for idx, item_data in enumerate(itens_data, start=1):
            # Calcular subtotal do item
            item_subtotal = float(item_data.get('item_quan', 0)) * float(item_data.get('item_unit', 0))
            
            # Calcular caixas e quantidade corretamente
            # Buscar dados de cálculo do frontend
            dados_calculo = item_data.get('dados_calculo', {})
            metragem_ambiente = float(dados_calculo.get('metragem_total', item_data.get('tamanho_m2', item_data.get('item_m2', 0))))
            m2_por_caixa = float(dados_calculo.get('m2_por_caixa', item_data.get('m2_por_caixa', 1)))
            
            # Se ainda não temos dados, usar valores do item_data diretamente
            if metragem_ambiente == 0:
                metragem_ambiente = float(item_data.get('area_m2', 0))
            
            # Caixas necessárias (arredondar para cima)
            import math
            caixas_necessarias = math.ceil(metragem_ambiente / m2_por_caixa) if m2_por_caixa > 0 else 0
            
            # Quantidade = metro quadrado/caixa * total de caixas
            quantidade = m2_por_caixa * caixas_necessarias
            
            # Limpar campos que serão passados explicitamente
            item_data_clean = item_data.copy()
            item_data_clean.pop('item_empr', None)
            item_data_clean.pop('item_fili', None)
            item_data_clean.pop('item_pedi', None)
            item_data_clean.pop('item_ambi', None)
            item_data_clean.pop('item_nume', None)
            item_data_clean.pop('item_suto', None)
            item_data_clean.pop('item_quan', None)  # Remove para evitar duplicação
            item_data_clean.pop('tamanho_m2', None)
            item_data_clean.pop('m2_por_caixa', None)
            item_data_clean.pop('caixas_necessarias', None)

            Itenspedidospisos.objects.using(banco).create(
                item_empr=pedido.pedi_empr,
                item_fili=pedido.pedi_fili,
                item_pedi=pedido.pedi_nume,
                item_ambi=idx,  # Sequencial por ambiente
                item_nume=idx,
                item_m2=metragem_ambiente,  # Metragem informada
                item_quan=quantidade,  # Quantidade = metragem
                item_caix=caixas_necessarias,  # Caixas calculadas
                item_prod_nome=item_data.get('item_nome_ambi', ''),  # Nome do ambiente
                item_nome_ambi=item_data.get('item_nome_ambi', ''),  # Nome do ambiente
                item_suto=item_subtotal,
                **item_data_clean
            )
        print('Pedido atualizado:',pedido)

        return pedido  
        
    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        # Aceitar tanto 'itens_input' quanto 'itens' - SEM VALIDAÇÃO DO SERIALIZER
        itens_data = validated_data.pop('itens_input', None)
        if itens_data is None:
            itens_data = validated_data.pop('itens', None)
        
        # Pegar dados brutos dos itens do request.data
        request = self.context.get('request')
        if request and hasattr(request, 'data'):
            itens_data = request.data.get('itens_input') or request.data.get('itens', [])
        
        if not itens_data:
            raise ValidationError("Itens do pedido são obrigatórios.")

        print(f"DEBUG: Processando pedido {instance.pedi_nume}")
        print(f"DEBUG: Número de itens recebidos: {len(itens_data)}")

        # Calcular valores totais
        subtotal = sum(
            float(item.get('item_quan', 0)) * float(item.get('item_unit', 0))
            for item in itens_data
        )
        desconto = sum(float(item.get('item_desc', 0)) for item in itens_data)
        total = subtotal - desconto
        
        validated_data['pedi_tota'] = total
        validated_data['pedi_desc'] = desconto

        # Atualiza campos do pedido
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)

        # Remove TODOS os itens antigos
        print(f"DEBUG: Removendo itens antigos do pedido {instance.pedi_nume}")
        deleted_count = Itenspedidospisos.objects.using(banco).filter(
            item_empr=instance.pedi_empr,
            item_fili=instance.pedi_fili,
            item_pedi=instance.pedi_nume
        ).delete()
        print(f"DEBUG: {deleted_count[0]} itens removidos")

        # Recria os itens (IGUAL AO CREATE)
        for idx, item_data in enumerate(itens_data, start=1):
            try:
                # Calcular subtotal do item
                item_subtotal = float(item_data.get('item_quan', 0)) * float(item_data.get('item_unit', 0))
                
                # Calcular caixas e quantidade corretamente
                # Buscar dados de cálculo do frontend
                dados_calculo = item_data.get('dados_calculo', {})
                metragem_ambiente = float(dados_calculo.get('metragem_total', item_data.get('tamanho_m2', item_data.get('item_m2', 0))))
                m2_por_caixa = float(dados_calculo.get('m2_por_caixa', item_data.get('m2_por_caixa', 1)))
                
                # Se ainda não temos dados, usar valores do item_data diretamente
                if metragem_ambiente == 0:
                    metragem_ambiente = float(item_data.get('area_m2', 0))
                
                # Caixas necessárias (arredondar para cima)
                import math
                caixas_necessarias = math.ceil(metragem_ambiente / m2_por_caixa) if m2_por_caixa > 0 else 0
                
                # Quantidade = metro quadrado/caixa * total de caixas
                quantidade = m2_por_caixa * caixas_necessarias
                print(f"DEBUG: Item {idx} - Metragem: {metragem_ambiente} m2, M2 por caixa: {m2_por_caixa}, Caixas: {caixas_necessarias}, Quantidade: {quantidade}")
                
                # Criar item diretamente sem validação do serializer
                item = Itenspedidospisos.objects.using(banco).create(
                    item_empr=instance.pedi_empr,
                    item_fili=instance.pedi_fili,
                    item_pedi=instance.pedi_nume,
                    item_ambi=idx,  # Sequencial por ambiente
                    item_nume=idx,
                    item_m2=metragem_ambiente,  # Metragem informada
                    item_quan=quantidade,  # Quantidade = metragem
                    item_caix=caixas_necessarias,  # Caixas calculadas
                    item_prod_nome=item_data.get('item_nome_ambi', ''),  # Nome do ambiente
                    item_nome_ambi=item_data.get('item_nome_ambi', ''),  # Nome do ambiente
                    item_suto=item_subtotal,
                    item_prod=item_data.get('item_prod'),
                    item_unit=item_data.get('item_unit', 0),
                    item_desc=item_data.get('item_desc', 0),
                    item_obse=item_data.get('item_obse', ''),
                    item_larg=item_data.get('item_larg', 0),
                    item_comp=item_data.get('item_comp', 0),
                    item_espe=item_data.get('item_espe', 0),
                    item_metr=item_data.get('item_metr', 0)
                )
                print(f"DEBUG: Item {idx} criado com sucesso - ID: {item.item_nume}")
            except Exception as e:
                print(f"DEBUG: Erro ao criar item {idx}: {e}")
                raise ValidationError(f"Erro ao criar item {idx}: {e}")
        
        print(f'DEBUG: Pedido atualizado com sucesso: {instance.pedi_nume}')
        return instance