from rest_framework import serializers
from .models import ImplantacaoTela

class ImplantacaoTelaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImplantacaoTela
        fields = '__all__'
