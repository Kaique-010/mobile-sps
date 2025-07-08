from rest_framework import serializers
from .models import (
    ParametrosGerais, PermissoesModulos, PermissoesRotas,
    ConfiguracaoEstoque, ConfiguracaoFinanceiro, LogParametros
)
from core.serializers import BancoContextMixin
import json

class ParametrosGeraisSerializer(BancoContextMixin, serializers.ModelSerializer):
    valor_typed = serializers.SerializerMethodField()
    
    class Meta:
        model = ParametrosGerais
        fields = '__all__'
        read_only_fields = ('para_codi', 'para_data_cria', 'para_data_alte')
    
    def get_valor_typed(self, obj):
        return obj.get_valor_typed()
    
    def validate_para_valo(self, value):
        """Valida o valor baseado no tipo"""
        para_tipo = self.initial_data.get('para_tipo', 'string')
        
        try:
            if para_tipo == 'boolean':
                if value.lower() not in ['true', 'false', '1', '0', 'sim', 'não', 'yes', 'no']:
                    raise serializers.ValidationError("Valor booleano inválido")
            elif para_tipo == 'integer':
                int(value)
            elif para_tipo == 'decimal':
                float(value)
            elif para_tipo == 'json':
                json.loads(value)
        except (ValueError, json.JSONDecodeError):
            raise serializers.ValidationError(f"Valor inválido para o tipo {para_tipo}")
        
        return value

class PermissoesModulosSerializer(BancoContextMixin, serializers.ModelSerializer):
    is_vencido = serializers.ReadOnlyField()
    modulos_disponiveis = serializers.SerializerMethodField()
    
    class Meta:
        model = PermissoesModulos
        fields = '__all__'
        read_only_fields = ('perm_codi', 'perm_data_libe')
    
    def get_modulos_disponiveis(self, obj):
        """Lista todos os módulos disponíveis no sistema"""
        from core.licenca_context import LICENCAS_MAP
        modulos_sistema = set()
        for licenca in LICENCAS_MAP:
            modulos_sistema.update(licenca.get('modulos', []))
        return sorted(list(modulos_sistema))

class PermissoesRotasSerializer(BancoContextMixin, serializers.ModelSerializer):
    class Meta:
        model = PermissoesRotas
        fields = '__all__'
        read_only_fields = ('rota_codi', 'rota_data_cria')

class ConfiguracaoEstoqueSerializer(BancoContextMixin, serializers.ModelSerializer):
    class Meta:
        model = ConfiguracaoEstoque
        fields = '__all__'
        read_only_fields = ('conf_codi', 'conf_data_alte')
    
    def validate(self, data):
        """Validações de negócio"""
        if data.get('conf_custo_medio') and data.get('conf_custo_ulti'):
            raise serializers.ValidationError(
                "Não é possível usar custo médio e último custo simultaneamente"
            )
        return data

class ConfiguracaoFinanceiroSerializer(BancoContextMixin, serializers.ModelSerializer):
    class Meta:
        model = ConfiguracaoFinanceiro
        fields = '__all__'
        read_only_fields = ('conf_codi', 'conf_data_alte')
    
    def validate_conf_desc_maxi_pedi(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Desconto deve estar entre 0 e 100%")
        return value

class LogParametrosSerializer(serializers.ModelSerializer):
    valor_anterior_json = serializers.SerializerMethodField()
    valor_novo_json = serializers.SerializerMethodField()
    
    class Meta:
        model = LogParametros
        fields = '__all__'
        read_only_fields = (
            'log_codi', 'log_tabe', 'log_regi_codi', 'log_camp', 
            'log_valo_ante', 'log_valo_novo', 'log_usua', 'log_data'
        )
    
    def get_valor_anterior_json(self, obj):
        try:
            return json.loads(obj.log_valo_ante) if obj.log_valo_ante else None
        except json.JSONDecodeError:
            return obj.log_valo_ante
    
    def get_valor_novo_json(self, obj):
        try:
            return json.loads(obj.log_valo_novo) if obj.log_valo_novo else None
        except json.JSONDecodeError:
            return obj.log_valo_novo