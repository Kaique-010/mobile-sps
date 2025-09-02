from rest_framework import serializers
from .models import (
    Modulo, PermissaoModulo, LogParametroSistema, ParametroSistema
)
from Licencas.models import Empresas, Filiais

# Removido PermissaoTelaSerializer pois o modelo não existe

class ModuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modulo
        fields = '__all__'
        read_only_fields = ['modu_codi']



class PermissaoModuloSerializer(serializers.ModelSerializer):
    modulo_nome = serializers.CharField(source='perm_modu.modu_nome', read_only=True)
    modulo_desc = serializers.CharField(source='perm_modu.modu_desc', read_only=True)
    empresa_nome = serializers.SerializerMethodField()
    filial_nome = serializers.SerializerMethodField()
    is_vencido = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PermissaoModulo
        fields = '__all__'
        read_only_fields = ['perm_codi', 'perm_data_libe']


    def get_empresa_nome(self, obj):
        try:
            banco = self.context.get('banco')
            empresa = Empresas.objects.using(banco).get(empr_codi=obj.perm_empr)
            return empresa.empr_nome
        except Empresas.DoesNotExist:
            return f"Empresa {obj.perm_empr}"
    
    def get_filial_nome(self, obj):
        try:
            banco = self.context.get('banco')
            filial = Filiais.objects.using(banco).get(
                empr_empr=obj.perm_fili,
                empr_codi=obj.perm_empr
            )
            return filial.empr_nome
        except Filiais.DoesNotExist:
            return f"Filial {obj.perm_fili}"

class LogParametroSistemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogParametroSistema
        fields = '__all__'
        read_only_fields = ['log_codi', 'log_data']

# Serializers para operações específicas
class PermissaoModuloCreateSerializer(serializers.ModelSerializer):
    modulos = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        help_text="Lista de IDs dos módulos"
    )
    empresas_filiais = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        help_text="Lista de {empresa_id, filial_id}"
    )
    
    class Meta:
        model = PermissaoModulo
        fields = ['modulos', 'empresas_filiais', 'perm_ativ', 'perm_data_venc', 'perm_limi_usua']
    
    def create(self, validated_data):
        modulos_ids = validated_data.pop('modulos')
        empresas_filiais = validated_data.pop('empresas_filiais')
        banco = self.context.get('banco')
        usuario_id = self.context.get('usuario_id')
        
        permissoes_criadas = []
        
        for empresa_filial in empresas_filiais:
            empresa_id = empresa_filial['empresa_id']
            filial_id = empresa_filial['filial_id']
            
            for modulo_id in modulos_ids:
                permissao, created = PermissaoModulo.objects.using(banco).get_or_create(
                    perm_empr=empresa_id,
                    perm_fili=filial_id,
                    perm_modu_id=modulo_id,
                    defaults={
                        'perm_ativ': validated_data.get('perm_ativ', True),
                        'perm_data_venc': validated_data.get('perm_data_venc'),
                        'perm_limi_usua': validated_data.get('perm_limi_usua'),
                        'perm_usua_libe': usuario_id
                    }
                )
                
                if not created:
                    # Atualizar permissão existente
                    for field, value in validated_data.items():
                        setattr(permissao, field, value)
                    permissao.perm_usua_libe = usuario_id
                    permissao.save(using=banco)
                
                permissoes_criadas.append(permissao)
        
        return permissoes_criadas[0] if permissoes_criadas else None


class ParametroSistemaSerializer(serializers.ModelSerializer):
    modulo_nome = serializers.CharField(source='para_modu.modu_nome', read_only=True)
    modulo_desc = serializers.CharField(source='para_modu.modu_desc', read_only=True)
    
    class Meta:
        model = ParametroSistema
        fields = '__all__'
        read_only_fields = ['para_codi', 'para_data_alte']


class ParametroSistemaUpdateSerializer(serializers.ModelSerializer):
    """Serializer para atualização de parâmetros"""
    
    class Meta:
        model = ParametroSistema
        fields = ['para_valo', 'para_ativ']
    
    def update(self, instance, validated_data):
        instance.para_valo = validated_data.get('para_valo', instance.para_valo)
        instance.para_ativ = validated_data.get('para_ativ', instance.para_ativ)
        instance.para_usua_alte = self.context.get('usuario_id', 1)
        instance.save()
        return instance
