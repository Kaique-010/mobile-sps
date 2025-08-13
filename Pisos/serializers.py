from rest_framework import serializers
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
    itens = serializers.SerializerMethodField()  # Mudança aqui - remover write_only
    itens_input = ItensorcapisosSerializer(many=True, write_only=True, required=False)
    
    
    class Meta:
        model = Orcamentopisos
        fields = '__all__'

    def get_itens(self, obj):
        banco = self.context.get('banco')
        itens = Itensorcapisos.objects.using(banco).filter(
            item_empr=obj.orca_empr,
            item_fili=obj.orca_fili,
            item_orca=str(obj.orca_nume)
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



        

class ItenspedidospisosSerializer(BancoContextMixin, serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField()
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
    itens = serializers.SerializerMethodField()
    itens_input = ItenspedidospisosSerializer(many=True, write_only=True, required=False)
    
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
