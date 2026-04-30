from rest_framework import serializers
from Pisos.services.orcamento_criar_service import OrcamentoCriarService
from Pisos.services.orcamento_atualizar_service import OrcamentoAtualizarService
from Pisos.services.pedido_criar_service import PedidoCriarService
from Pisos.services.pedido_atualizar_service import PedidoAtualizarService
from rest_framework.exceptions import ValidationError
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from core.serializers import BancoContextMixin
from .models import Orcamentopisos, Itensorcapisos, Itenspedidospisos, Pedidospisos   
from Licencas.models import Empresas
from Produtos.models import Produtos   
from Entidades.models import Entidades
from datetime import date, datetime, timedelta
from .services.preco_service import get_preco_produto
from .services.utils_service import parse_decimal, arredondar
from .services.calculo_services import calcular_item, calcular_ambientes, calcular_total_geral
import logging

logger = logging.getLogger(__name__)    



class ItensorcapisosSerializer(serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField()
    item_nume = serializers.IntegerField(read_only=True)

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
    vendedor_nome = serializers.SerializerMethodField()
    itens = serializers.SerializerMethodField(read_only=True)
    # Aceitar itens como lista de dicts para evitar validação estrita de decimais
    itens_input = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    parametros = serializers.DictField(write_only=True, required=False)
    orca_nume = serializers.IntegerField(read_only=True)  
    # Totais serão calculados no backend; evitar validação do valor enviado
    orca_tota = serializers.DecimalField(max_digits=15, decimal_places=4, read_only=True)
    orca_desc = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    orca_fret = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    item_ambi = serializers.IntegerField(required=False, allow_null=True)
    

    
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
        
    def get_vendedor_nome(self, obj):
        # Tentar usar cache primeiro
        vendedores_cache = self.context.get('vendedores_cache')
        if vendedores_cache:
            return vendedores_cache.get(obj.orca_vend)
        
        # Fallback para consulta individual
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            vendedor = Entidades.objects.using(banco).filter(enti_clie=obj.orca_vend).first()
            return vendedor.enti_nome if vendedor else None
        except Exception as e:
            logger.warning(f"Erro ao buscar vendedor: {e}")
            return None

    def create(self, validated_data):
        banco = self.context.get("banco")

        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        itens_data = validated_data.pop("itens_input", None)

        if itens_data is None:
            request = self.context.get("request")
            if request and hasattr(request, "data"):
                itens_data = request.data.get("itens_input") or request.data.get("itens")

        itens_data = itens_data or []

        try:
            return OrcamentoCriarService().executar(
                banco=banco,
                dados=validated_data,
                itens=itens_data,
            )
        except ValueError as exc:
            raise ValidationError(str(exc))

    

    def update(self, instance, validated_data):
        banco = self.context.get("banco")

        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        itens_data = validated_data.pop("itens_input", None)

        if itens_data is None:
            request = self.context.get("request")
            if request and hasattr(request, "data"):
                itens_data = request.data.get("itens_input") or request.data.get("itens")

        itens_data = itens_data or []

        try:
            return OrcamentoAtualizarService().executar(
                banco=banco,
                orcamento=instance,
                dados=validated_data,
                itens=itens_data,
            )
        except ValueError as exc:
            raise ValidationError(str(exc))

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
    pedi_desc = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    pedi_fret = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    item_ambi = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        model = Pedidospisos
        fields = '__all__'

    def get_itens(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return []
        try:
            itens = Itenspedidospisos.objects.using(banco).filter(
                item_empr=obj.pedi_empr,
                item_fili=obj.pedi_fili,
                item_pedi=obj.pedi_nume
            )
            return ItenspedidospisosSerializer(itens, many=True, context=self.context).data
        except Exception as e:
            logger.error(f"Erro ao buscar itens do pedido {obj.pedi_nume}: {e}")
            return []

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
                item_empr=obj.pedi_empr,
                item_fili=obj.pedi_fili,
                item_pedi=obj.pedi_nume
            ).values_list('item_ambi', flat=True).distinct()
            return calcular_ambientes(ambientes)
        except Exception as e:
            logger.error(f"Erro ao buscar ambientes: {e}")
            return None
    
    
    def _salvar_itens(self, pedido, itens_input, banco):
        Itenspedidospisos.objects.using(banco).filter(
            item_empr=pedido.pedi_empr,
            item_fili=pedido.pedi_fili,
            item_pedi=pedido.pedi_nume,
        ).delete()

        for idx, item_data in enumerate(itens_input, start=1):
            prod_id = item_data.get("item_prod")
            
            # Buscar o produto para passar ao service
            produto = None
            if prod_id:
                produto = Produtos.objects.using(banco).filter(prod_codi=prod_id).first()

            # Calcular caixas, quantidade e total via service
            # Criamos um objeto temporário duck-typed para o service
            class ItemProxy:
                item_m2 = item_data.get("item_m2") or 0
                item_queb = item_data.get("item_queb") or 0
                item_unit = item_data.get("item_unit") or 0

            resultado = calcular_item(ItemProxy(), produto=produto)

            Itenspedidospisos.objects.using(banco).create(
                item_empr=pedido.pedi_empr,
                item_fili=pedido.pedi_fili,
                item_pedi=pedido.pedi_nume,
                item_nume=idx,
                item_prod=prod_id,
                item_prod_nome=item_data.get("item_prod_nome", ""),
                item_ambi=item_data.get("item_ambi") or 1,
                item_nome_ambi=item_data.get("item_nome_ambi", ""),
                item_m2=item_data.get("item_m2") or 0,
                item_queb=item_data.get("item_queb") or 0,
                item_unit=item_data.get("item_unit") or 0,
                item_desc=item_data.get("item_desc") or 0,
                item_obse=item_data.get("item_obse", ""),
                # ↓ Preenchidos pelo service
                item_caix=resultado["caixas_necessarias"] or 0,
                item_quan=resultado["metragem_real"],
                item_suto=resultado["total"],
            )

    def create(self, validated_data):
        banco = self.context.get("banco")

        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        itens_data = validated_data.pop("itens_input", None)

        if itens_data is None:
            request = self.context.get("request")
            if request and hasattr(request, "data"):
                itens_data = request.data.get("itens_input") or request.data.get("itens")

        itens_data = itens_data or []

        try:
            return PedidoCriarService().executar(
                banco=banco,
                dados=validated_data,
                itens=itens_data,
            )
        except ValueError as exc:
            raise ValidationError(str(exc))
        
    def update(self, instance, validated_data):
        banco = self.context.get("banco")

        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        itens_data = validated_data.pop("itens_input", None)

        if itens_data is None:
            request = self.context.get("request")
            if request and hasattr(request, "data"):
                itens_data = request.data.get("itens_input") or request.data.get("itens")

        itens_data = itens_data or []

        try:
            return PedidoAtualizarService().executar(
                banco=banco,
                pedido=instance,
                dados=validated_data,
                itens=itens_data,
            )
        except ValueError as exc:
            raise ValidationError(str(exc))
