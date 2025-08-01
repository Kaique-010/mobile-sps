from rest_framework import serializers
from .models import Ordemproducao, Ordemprodfotos, Ordemproditens, Ordemprodmate, Ordemprodetapa
from Entidades.models import Entidades
import logging

logger = logging.getLogger(__name__)

class OrdemproducaoSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.SerializerMethodField(read_only=True)
    fotos = serializers.SerializerMethodField(read_only=True)
    itens = serializers.SerializerMethodField(read_only=True)
    materiais = serializers.SerializerMethodField(read_only=True)
    etapas = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Ordemproducao
        fields = '__all__'
    
    def get_cliente_nome(self, obj):
        banco = self.context.get('banco')
        if not banco or not obj.orpr_clie:
            return None
            
        try:
            entidade = Entidades.objects.using(banco).filter(
                enti_clie=obj.orpr_clie,
                enti_empr=obj.orpr_empr
            ).first()
            return entidade.enti_nome if entidade else None
        except Exception as e:
            logger.error(f"Erro ao buscar cliente: {e}")
            return None
    
    def get_fotos(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return []
        
        fotos = Ordemprodfotos.objects.using(banco).filter(
            orpr_codi=obj.orpr_codi,
            orpr_empr=obj.orpr_empr,
            orpr_fili=obj.orpr_fili
        )
        return OrdemprodfotosSerializer(fotos, many=True, context=self.context).data
    
    def get_itens(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return []
        
        itens = Ordemproditens.objects.using(banco).filter(
            orpr_codi=obj.orpr_codi,
            orpr_fili=obj.orpr_fili
        )
        return OrdemproditensSerializer(itens, many=True, context=self.context).data
    
    def get_materiais(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return []
        
        materiais = Ordemprodmate.objects.using(banco).filter(
            orpm_orpr=obj.orpr_codi
        )
        return OrdemprodmateSerializer(materiais, many=True, context=self.context).data
    
    def get_etapas(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return []
        
        etapas = Ordemprodetapa.objects.using(banco).filter(
            opet_orpr=obj.orpr_codi
        )
        return OrdemprodetapaSerializer(etapas, many=True, context=self.context).data

class OrdemprodfotosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ordemprodfotos
        fields = '__all__'

class OrdemproditensSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ordemproditens
        fields = '__all__'

class OrdemprodmateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ordemprodmate
        fields = '__all__'

class OrdemprodetapaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ordemprodetapa
        fields = '__all__'
