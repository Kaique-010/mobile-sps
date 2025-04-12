from rest_framework import serializers
from .models import Empresas, Filiais, UserEmpresaFilial

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresas
        fields = ['empr_codi', 'empr_nome', 'empr_docu']


class FilialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Filiais
        fields = ['empr_codi', 'empr_nome']


class UserEmpresaFilialSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserEmpresaFilial
        fields = '__all__'
