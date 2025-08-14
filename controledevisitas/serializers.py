from rest_framework import serializers
from rest_framework import status
from django.db.models import Max
from .models import Controlevisita, Etapavisita
from Entidades.models import Entidades
from Licencas.models import Empresas
from core.utils import get_licenca_db_config
from rest_framework.exceptions import NotFound
import logging

logger = logging.getLogger(__name__)


class ControleVisitaSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.SerializerMethodField()
    vendedor_nome = serializers.SerializerMethodField()
    empresa_nome = serializers.SerializerMethodField()
    km_percorrido = serializers.SerializerMethodField()
    etapa_display = serializers.CharField(source='get_ctrl_etapa_display', read_only=True)
    etapa_descricao = serializers.SerializerMethodField()
    
    class Meta:
        model = Controlevisita
        fields = [
            'ctrl_id',
            'ctrl_empresa',
            'ctrl_filial', 
            'ctrl_numero',
            'ctrl_cliente',
            'ctrl_data',
            'ctrl_novo',
            'ctrl_base',
            'ctrl_prop',
            'ctrl_leva',
            'ctrl_proj',
            'ctrl_etapa',
            'ctrl_vendedor',
            'ctrl_obse',
            'ctrl_contato',
            'ctrl_fone',
            'ctrl_km_inic',
            'ctrl_km_fina',
            'ctrl_prox_visi',
            'ctrl_nume_orca',
            'cliente_nome',
            'vendedor_nome',
            'empresa_nome',
            'km_percorrido',
            'etapa_display',
            'etapa_descricao',
           
        ]
        read_only_fields = ['ctrl_id', 'field_log_data', 'field_log_time']


    def validate(self, data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        
        erros = {}
        obrigatorios = ['ctrl_empresa', 'ctrl_filial', 'ctrl_data', 'ctrl_cliente']
        
        for campo in obrigatorios:
            if not data.get(campo):
                erros[campo] = ['Este campo é obrigatório.']
        
        # Validar se KM final é maior que inicial
        if data.get('ctrl_km_inic') and data.get('ctrl_km_fina'):
            if data['ctrl_km_fina'] < data['ctrl_km_inic']:
                erros['ctrl_km_fina'] = ['KM final deve ser maior que KM inicial.']
        
        if erros:
            raise serializers.ValidationError(erros)
        
        return data
    
    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        
        # Gerar próximo número se não fornecido
        if not validated_data.get('ctrl_numero'):
            max_numero = Controlevisita.objects.using(banco).filter(
                ctrl_empresa=validated_data['ctrl_empresa'],
                ctrl_filial=validated_data['ctrl_filial']
            ).aggregate(Max('ctrl_numero'))['ctrl_numero__max'] or 0
            validated_data['ctrl_numero'] = max_numero + 1
        
        return Controlevisita.objects.using(banco).create(**validated_data)
    
    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)
        return instance

    def get_cliente_nome(self, obj):
        banco = self.context.get('banco')
        if not banco or not obj.ctrl_cliente:
            return None
        
        try:
            return obj.ctrl_cliente.enti_nome
        except Exception as e:
            logger.warning(f"Erro ao buscar nome do cliente: {e}")
            return None

    def get_vendedor_nome(self, obj):
        banco = self.context.get('banco')
        if not banco or not obj.ctrl_vendedor:
            return None
        
        try:
            return obj.ctrl_vendedor.enti_nome
        except Exception as e:
            logger.warning(f"Erro ao buscar nome do vendedor: {e}")
            return None

    def get_empresa_nome(self, obj):
        banco = self.context.get('banco')
        if not banco or not obj.ctrl_empresa:
            return None
        
        try:
            return obj.ctrl_empresa.empr_nome
        except Exception as e:
            logger.warning(f"Erro ao buscar nome da empresa: {e}")
            return None

    def get_km_percorrido(self, obj):
        return obj.km_percorrido


    def get_etapa_descricao(self, obj):
        if obj.ctrl_etapa:
            return obj.ctrl_etapa.etap_descricao
        return None

class EtapaVisitaSerializer(serializers.ModelSerializer):
    empresa_nome = serializers.SerializerMethodField()
    
    class Meta:
        model = Etapavisita
        fields = [
            'etap_id',
            'etap_nume', 
            'etap_descricao',
            'etap_empr',
            'etap_obse',
            'empresa_nome'
        ]
        read_only_fields = ['etap_id']
    
    def validate(self, data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        
        erros = {}
        obrigatorios = ['etap_empr', 'etap_nume', 'etap_descricao']
        
        for campo in obrigatorios:
            if not data.get(campo):
                erros[campo] = ['Este campo é obrigatório.']
        
        if erros:
            raise serializers.ValidationError(erros)
        
        return data
    
    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        
        return Etapavisita.objects.using(banco).create(**validated_data)
    
    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)
        return instance
    
    def get_empresa_nome(self, obj):
        banco = self.context.get('banco')
        if not banco or not obj.etap_empr:
            return None
        
        try:
            return obj.etap_empr.empr_nome
        except Exception as e:
            logger.warning(f"Erro ao buscar nome da empresa: {e}")
            return None
    
    def get_etapa_descricao(self, obj):
        if obj.ctrl_etapa:
            return obj.ctrl_etapa.etap_descricao
        return None




