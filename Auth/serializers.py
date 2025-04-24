from rest_framework import serializers
from .models import Empresas, Filiais

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresas
        fields = ['empr_codi', 'empr_nome', 'empr_docu']


class FilialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Filiais
        fields = ['empr_codi', 'empr_nome']


