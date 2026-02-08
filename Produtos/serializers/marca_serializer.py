from rest_framework import serializers
from ..models import Marca
from core.serializers import BancoContextMixin

class MarcaSerializer(BancoContextMixin, serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = ['codigo', 'nome']
