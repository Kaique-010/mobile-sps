from rest_framework import serializers
from .models import Empresas, Filiais, Usuarios
from core.serializers import BancoContextMixin
from django.db.models import Max
from .utils import get_proximo_usuario



class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresas
        fields = ['empr_codi', 'empr_nome', 'empr_docu']


class FilialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Filiais
        fields = ['empr_codi', 'empr_nome']


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

