from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from core.serializers import BancoContextMixin
from .models import Orcamentopisos, Itensorcapisos, Itenspedidospisos, Pedidospisos   
from Licencas.models import Empresas
from Produtos.models import Produtos   
from Entidades.models import Entidades
from .preco_service import get_preco_produto
from .utils_service import parse_decimal, arredondar
from .calculo_services import calcular_item, calcular_ambientes, calcular_total_geral
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
    ambientes = serializers.SerializerMethodField(read_only=True)
    
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

    def get_ambientes(self, obj):
        banco = self.context.get('banco')
        itens = Itensorcapisos.objects.using(banco).filter(
            item_empr=obj.orca_empr,
            item_fili=obj.orca_fili,
            item_orca=obj.orca_nume
        )
        return calcular_ambientes(itens)
        
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
        banco = self.context.get("banco")
        itens_data = validated_data.pop("itens_input", [])

        if not itens_data:
            raise ValidationError("Itens do orçamento são obrigatórios.")

        # Cria orçamento base
        ultimo = Orcamentopisos.objects.using(banco).filter(
            orca_empr=validated_data["orca_empr"],
            orca_fili=validated_data["orca_fili"]
        ).order_by("-orca_nume").first()
        validated_data["orca_nume"] = (ultimo.orca_nume + 1) if ultimo else 1

        orcamento = Orcamentopisos.objects.using(banco).create(**validated_data)

        # Cria itens mapeando dados do frontend (dados_calculo) e somando item_suto
        itens_objs = []
        def q2(value):
            try:
                d = Decimal(str(value))
                return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except Exception:
                return None
        allowed_fields = {f.name for f in Itensorcapisos._meta.fields}
        for idx, item_data in enumerate(itens_data, start=1):
            item_data_clean = item_data.copy()
            # Remover campos que serão definidos explicitamente
            for k in ["item_suto", "item_empr", "item_fili", "item_orca", "item_nume"]:
                item_data_clean.pop(k, None)

            # Mapear campos do frontend
            if "area_m2" in item_data_clean:
                item_data_clean["item_m2"] = item_data_clean.pop("area_m2")
            if "observacoes" in item_data_clean:
                item_data_clean["item_obse"] = item_data_clean.pop("observacoes")

            # Processar dados de cálculo do frontend
            dados_calc = item_data_clean.pop("dados_calculo", None)
            if dados_calc:
                if "caixas_necessarias" in dados_calc and "item_caix" not in item_data_clean:
                    item_data_clean["item_caix"] = dados_calc.get("caixas_necessarias")
                if "m2_por_caixa" in dados_calc and "item_quan" not in item_data_clean:
                    try:
                        m2cx = float(dados_calc.get("m2_por_caixa") or 0)
                        caixas = float(item_data_clean.get("item_caix") or 0)
                        item_data_clean["item_quan"] = m2cx * caixas
                    except Exception:
                        pass

            # Filtrar apenas campos existentes no modelo
            item_data_clean = {k: v for k, v in item_data_clean.items() if k in allowed_fields}

            # Quantizar campos decimais
            for num_key in ["item_quan", "item_unit", "item_m2", "item_desc"]:
                if num_key in item_data_clean and item_data_clean[num_key] is not None:
                    qv = q2(item_data_clean[num_key])
                    if qv is not None:
                        item_data_clean[num_key] = qv

            # Subtotal = quantidade x unitário
            try:
                item_quan = Decimal(str(item_data_clean.get("item_quan") or 0))
                item_unit = Decimal(str(item_data_clean.get("item_unit") or 0))
                item_subtotal = q2(item_quan * item_unit) or Decimal("0.00")
            except Exception:
                item_subtotal = Decimal("0.00")

            item = Itensorcapisos.objects.using(banco).create(
                item_empr=orcamento.orca_empr,
                item_fili=orcamento.orca_fili,
                item_orca=orcamento.orca_nume,
                item_nume=idx,
                item_suto=item_subtotal,
                **item_data_clean,
            )
            itens_objs.append(item)

        # Atualiza total do orçamento somando item_suto dos itens criados
        def q2(value):
            try:
                d = Decimal(str(value))
                return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except Exception:
                return None
        total_geral = sum((Decimal(str(getattr(item, 'item_suto', 0))) for item in itens_objs), Decimal('0.00'))
        orcamento.orca_tota = q2(total_geral) or Decimal('0.00')
        orcamento.save(using=banco)

        return orcamento

    

    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        # Extrair itens
        itens_data = validated_data.pop('itens_input', [])
        if not itens_data:
            raise ValidationError("Itens do orçamento são obrigatórios.")

        # Helper de quantização
        def q2(value):
            try:
                d = Decimal(str(value))
                return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except Exception:
                return None

        # Totais com Decimal
        subtotal = sum(
            (Decimal(str(item.get('item_quan', 0))) * Decimal(str(item.get('item_unit', 0))))
            for item in itens_data
        )
        desconto = sum(Decimal(str(item.get('item_desc', 0))) for item in itens_data)
        total = subtotal - desconto

        instance.orca_tota = q2(total) or Decimal('0.00')
        instance.orca_desc = q2(desconto) or Decimal('0.00')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)

        # Remove itens antigos
        Itensorcapisos.objects.using(banco).filter(
            item_empr=instance.orca_empr,
            item_fili=instance.orca_fili,
            item_orca=instance.orca_nume
        ).delete()

        # Recriar itens com mapeamento de dados_calculo
        allowed_fields = {f.name for f in Itensorcapisos._meta.fields}
        for idx, item_data in enumerate(itens_data, start=1):
            item_data_clean = item_data.copy()
            item_data_clean.pop('item_suto', None)

            # Mapear campos específicos
            if 'area_m2' in item_data_clean:
                item_data_clean['item_m2'] = item_data_clean.pop('area_m2')
            if 'observacoes' in item_data_clean:
                item_data_clean['item_obse'] = item_data_clean.pop('observacoes')

            # Processar dados de cálculo do frontend
            dados_calculo = item_data_clean.pop('dados_calculo', None)
            if dados_calculo:
                import math
                m2_por_caixa = float(dados_calculo.get('m2_por_caixa', item_data_clean.get('m2_por_caixa', 1)))
                metragem_base = float(item_data_clean.get('item_m2', item_data.get('area_m2', 0)))
                caixas_necessarias = math.ceil(metragem_base / m2_por_caixa) if m2_por_caixa > 0 else 0
                if 'item_caix' not in item_data_clean:
                    item_data_clean['item_caix'] = caixas_necessarias
                if 'item_quan' not in item_data_clean:
                    item_data_clean['item_quan'] = m2_por_caixa * caixas_necessarias

            # Filtrar apenas campos existentes no modelo
            item_data_clean = {k: v for k, v in item_data_clean.items() if k in allowed_fields}

            # Subtotal do item com Decimal
            try:
                item_subtotal = Decimal(str(item_data_clean.get('item_quan', 0))) * Decimal(str(item_data_clean.get('item_unit', 0)))
                item_subtotal = q2(item_subtotal) or Decimal('0.00')
            except Exception:
                item_subtotal = Decimal('0.00')

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
    item_nume = serializers.IntegerField(read_only=True)

    
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
    vendedor_nome = serializers.SerializerMethodField()
    itens = serializers.SerializerMethodField(read_only=True)
    # Aceitar itens como lista de dicts para evitar validação estrita de decimais
    itens_input = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    parametros = serializers.DictField(write_only=True, required=False)
    pedi_nume = serializers.IntegerField(read_only=True)  
    # Totais serão calculados no backend; evitar validação do valor enviado
    pedi_tota = serializers.DecimalField(max_digits=15, decimal_places=4, read_only=True)
    pedi_desc = serializers.DecimalField(max_digits=15, decimal_places=4, read_only=True)
    item_ambi = serializers.IntegerField(required=False, allow_null=True)
    
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
    
    def get_vendedor_nome(self, obj):
        # Tentar usar cache primeiro
        vendedores_cache = self.context.get('vendedores_cache')
        if vendedores_cache:
            return vendedores_cache.get(obj.pedi_vend)
        
        # Fallback para consulta individual
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            vendedor = Entidades.objects.using(banco).filter(enti_clie=obj.pedi_vend).first()
            return vendedor.enti_nome if vendedor else None
        except Exception as e:
            logger.warning(f"Erro ao buscar vendedor: {e}")
            return None
    
    def get_ambientes(self, obj):
        banco = self.context.get('banco')
        if not banco:
            logger.warning("Banco não informado no context.")
            return None
        try:
            ambientes = Itenspedidospisos.objects.using(banco).filter(
                item_empr=obj.item_empr,
                item_fili=obj.item_fili,
                item_pedi=obj.item_pedi
            ).values_list('item_ambi', flat=True).distinct()
            return calcular_ambientes(ambientes)
        except Exception as e:
            logger.error(f"Erro ao buscar ambientes: {e}")
            return None

    def create(self, validated_data):
        banco = self.context.get("banco")
        # Aceitar itens tanto em 'itens_input' (padrão) quanto em 'itens' (fallback)
        itens_data = validated_data.pop("itens_input", None)
        if itens_data is None:
            # Tentar obter diretamente do request, caso o payload não siga o schema do serializer
            request = self.context.get("request")
            if request and hasattr(request, "data"):
                itens_data = request.data.get("itens_input") or request.data.get("itens")
        # Normalizar para lista vazia se ainda não definido
        itens_data = itens_data or []

        if not itens_data:
            raise ValidationError({"itens_input": ["Itens do pedido são obrigatórios. Envie uma lista em 'itens_input' ou 'itens'."]})

        ultimo = Pedidospisos.objects.using(banco).filter(
            pedi_empr=validated_data["pedi_empr"],
            pedi_fili=validated_data["pedi_fili"]
        ).order_by("-pedi_nume").first()
        validated_data["pedi_nume"] = (ultimo.pedi_nume + 1) if ultimo else 1

        pedido = Pedidospisos.objects.using(banco).create(**validated_data)

        # Helper para quantizar decimais com 4 casas
        def q2(value):
            try:
                d = Decimal(str(value))
                return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except Exception:
                return None

        itens_objs = []
        # Campos permitidos no modelo (evitar kwargs inesperados como 'produto_nome')
        allowed_fields = {f.name for f in Itenspedidospisos._meta.fields}
        for idx, item_data in enumerate(itens_data, start=1):
            # Limpa dados para evitar atributos internos e não-modelados
            item_data_clean = item_data.copy()
            # Remover campos que serão definidos explicitamente
            for k in [
                "item_suto", "item_empr", "item_fili",
                "item_pedi", "item_nume"
            ]:
                item_data_clean.pop(k, None)

            # Mapear campos do frontend para os do modelo
            if "area_m2" in item_data_clean:
                item_data_clean["item_m2"] = item_data_clean.pop("area_m2")
            if "observacoes" in item_data_clean:
                item_data_clean["item_obse"] = item_data_clean.pop("observacoes")

            # Se vier dados de cálculo do frontend, garantir coerência mínima
            dados_calc = item_data_clean.pop("dados_calculo", None)
            if dados_calc:
                if "caixas_necessarias" in dados_calc and "item_caix" not in item_data_clean:
                    item_data_clean["item_caix"] = dados_calc.get("caixas_necessarias")
                if "m2_por_caixa" in dados_calc and "item_quan" not in item_data_clean:
                    try:
                        m2cx = float(dados_calc.get("m2_por_caixa") or 0)
                        caixas = float(item_data_clean.get("item_caix") or 0)
                        item_data_clean["item_quan"] = m2cx * caixas
                    except Exception:
                        pass

            # Filtrar apenas campos existentes no modelo
            item_data_clean = {k: v for k, v in item_data_clean.items() if k in allowed_fields}

            # Quantizar campos decimais para evitar erros de max_digits
            for num_key in ["item_quan", "item_unit", "item_m2", "item_desc"]:
                if num_key in item_data_clean and item_data_clean[num_key] is not None:
                    qv = q2(item_data_clean[num_key])
                    if qv is not None:
                        item_data_clean[num_key] = qv

            # Calcular subtotal do item (quantidade x unitário)
            try:
                item_quan = Decimal(str(item_data_clean.get("item_quan") or 0))
                item_unit = Decimal(str(item_data_clean.get("item_unit") or 0))
                item_subtotal = q2(item_quan * item_unit) or Decimal("0.0000")
            except Exception:
                item_subtotal = Decimal("0.0000")

            # Criar item
            item = Itenspedidospisos.objects.using(banco).create(
                item_empr=pedido.pedi_empr,
                item_fili=pedido.pedi_fili,
                item_pedi=pedido.pedi_nume,
                item_nume=idx,
                item_suto=item_subtotal,
                **item_data_clean,
            )
            itens_objs.append(item)

        # Atualiza total do pedido somando item_suto dos itens criados
        total_geral = sum((Decimal(str(getattr(item, 'item_suto', 0))) for item in itens_objs), Decimal('0.00'))
        pedido.pedi_tota = q2(total_geral) if total_geral is not None else Decimal('0.00')
        pedido.save(using=banco)
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

        # Calcular valores totais (robusto a None) usando Decimal e quantização
        def q2(value):
            try:
                d = Decimal(str(value))
                return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except Exception:
                return None

        subtotal = sum(
            (Decimal(str(item.get('item_quan') or 0)) * Decimal(str(item.get('item_unit') or 0)))
            for item in itens_data
        )
        desconto = sum(Decimal(str(item.get('item_desc') or 0)) for item in itens_data)
        total = subtotal - desconto
        
        validated_data['pedi_tota'] = q2(total) or Decimal('0.00')
        validated_data['pedi_desc'] = q2(desconto) or Decimal('0.00')

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
                m2_por_caixa = float(dados_calculo.get('m2_por_caixa', item_data.get('m2_por_caixa', 1)))
                base_metragem = float(item_data.get('item_m2', item_data.get('tamanho_m2', item_data.get('area_m2', 0))))

                # Caixas necessárias (arredondar para cima)
                import math
                caixas_necessarias = math.ceil(base_metragem / m2_por_caixa) if m2_por_caixa > 0 else 0
                
                # Quantidade = metro quadrado/caixa * total de caixas
                quantidade = m2_por_caixa * caixas_necessarias
                print(f"DEBUG: Item {idx} - Metragem: {base_metragem} m2, M2 por caixa: {m2_por_caixa}, Caixas: {caixas_necessarias}, Quantidade: {quantidade}")
                
                # Criar item diretamente sem validação do serializer
                item = Itenspedidospisos.objects.using(banco).create(
                    item_empr=instance.pedi_empr,
                    item_fili=instance.pedi_fili,
                    item_pedi=instance.pedi_nume,
                    item_ambi=idx,  # Sequencial por ambiente
                    item_nume=idx,
                    item_m2=base_metragem,  # Preserva a metragem informada
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