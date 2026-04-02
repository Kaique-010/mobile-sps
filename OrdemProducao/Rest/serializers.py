from rest_framework import serializers

from ..models import Ordemproducao, Ordemprodfotos, Ordemproditens, Ordemprodmate, Ordemprodetapa
from ..services import OrdemProducaoService, OrdemProducaoFilhosService


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


class OrdemproducaoSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.SerializerMethodField(read_only=True)
    fotos = serializers.SerializerMethodField(read_only=True)
    itens = serializers.SerializerMethodField(read_only=True)
    materiais = serializers.SerializerMethodField(read_only=True)
    etapas = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Ordemproducao
        fields = '__all__'

    def _get_banco(self):
        return self.context.get('banco')

    def get_cliente_nome(self, obj):
        banco = self._get_banco()
        if not banco:
            return None
        return OrdemProducaoService.buscar_cliente_nome(using=banco, ordem=obj)

    def get_fotos(self, obj):
        banco = self._get_banco()
        if not banco:
            return []
        fotos = OrdemProducaoFilhosService.listar_fotos(ordem=obj, using=banco)
        return OrdemprodfotosSerializer(fotos, many=True, context=self.context).data

    def get_itens(self, obj):
        banco = self._get_banco()
        if not banco:
            return []
        itens = OrdemProducaoFilhosService.listar_itens(ordem=obj, using=banco)
        return OrdemproditensSerializer(itens, many=True, context=self.context).data

    def get_materiais(self, obj):
        banco = self._get_banco()
        if not banco:
            return []
        materiais = OrdemProducaoFilhosService.listar_materiais(ordem=obj, using=banco)
        return OrdemprodmateSerializer(materiais, many=True, context=self.context).data

    def get_etapas(self, obj):
        banco = self._get_banco()
        if not banco:
            return []
        etapas = OrdemProducaoFilhosService.listar_etapas(ordem=obj, using=banco)
        return OrdemprodetapaSerializer(etapas, many=True, context=self.context).data
