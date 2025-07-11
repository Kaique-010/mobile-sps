from rest_framework import serializers
from .models import (
    Modulo, PermissaoModulo, LogParametroSistema, ParametroSistema
)

# Removido PermissaoTelaSerializer pois o modelo não existe

class ModuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modulo
        fields = '__all__'
        read_only_fields = ['modu_codi']



class PermissaoModuloSerializer(serializers.ModelSerializer):
    modulo_nome = serializers.CharField(source='perm_modu.modu_nome', read_only=True)
    modulo_desc = serializers.CharField(source='perm_modu.modu_desc', read_only=True)
    is_vencido = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PermissaoModulo
        fields = '__all__'
        read_only_fields = ['perm_codi', 'perm_data_libe']




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
    
    class Meta:
        model = PermissaoModulo
        fields = ['perm_empr', 'perm_fili', 'modulos']
    
    def create(self, validated_data):
        modulos_ids = validated_data.pop('modulos')
        banco = self.context.get('banco')
        
        permissoes_criadas = []
        for modulo_id in modulos_ids:
            try:
                modulo = Modulo.objects.get(modu_codi=modulo_id)
                permissao, created = PermissaoModulo.objects.using(banco).get_or_create(
                    perm_empr=validated_data['perm_empr'],
                    perm_fili=validated_data['perm_fili'],
                    perm_modu=modulo,
                    defaults={
                        'perm_ativ': True,
                        'perm_usua_libe': self.context.get('usuario', '')
                    }
                )
                if created:
                    permissoes_criadas.append(permissao)
            except Modulo.DoesNotExist:
                continue
        
        return {'permissoes_criadas': len(permissoes_criadas)}


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
