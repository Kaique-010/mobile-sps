from rest_framework import serializers
from .models import Empresas, Filiais, Usuarios
from Licencas.crypto import decrypt_str
from core.serializers import BancoContextMixin
from django.db.models import Max
from .utils import get_proximo_usuario, get_proxima_empresa, get_proxima_filial



class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresas
        fields = ['empr_codi', 'empr_nome', 'empr_docu']


class FilialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Filiais
        # Inclui o identificador primário da filial (empr_empr) para uso no front
        fields = ['empr_empr', 'empr_codi', 'empr_nome']

class EmpresaDetailSerializer(serializers.ModelSerializer):
    
    def create(self, validated_data):
        banco = self.context.get('banco')
        empr_codi = get_proxima_empresa(banco)
        validated_data['empr_codi'] = empr_codi
        return Empresas.objects.using(banco).create(**validated_data)
    class Meta:
        model = Empresas
        fields = '__all__'

class FilialDetailSerializer(serializers.ModelSerializer):
    has_certificado = serializers.SerializerMethodField()
    certificado_nome = serializers.SerializerMethodField()
    senha_mascarada = serializers.SerializerMethodField()

    class Meta:
        model = Filiais
        fields = '__all__'

    def get_has_certificado(self, obj):
        return bool(obj.empr_cert_digi)

    def get_certificado_nome(self, obj):
        return obj.empr_cert or None

    def get_senha_mascarada(self, obj):
        return '********' if obj.empr_senh_cert else ''


class UsuarioSerializer(BancoContextMixin, serializers.ModelSerializer):
    usua_codi = serializers.IntegerField(required=False, read_only=True)

    class Meta:
        model = Usuarios
        fields = ['usua_codi', 'usua_nome', 'password']

    def create(self, validated_data):
        banco = self.context.get('banco')
        usua_codi = get_proximo_usuario(banco)
        validated_data['usua_codi'] = usua_codi
        return Usuarios.objects.using(banco).create(**validated_data)

