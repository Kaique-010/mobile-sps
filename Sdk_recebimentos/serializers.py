
from rest_framework import serializers
from .models import RecebimentoSdk, TituloReceberSdk

class RecebimentoSdkSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecebimentoSdk
        fields = '__all__'



class TituloReceberSdkSerializer(serializers.ModelSerializer):
    class Meta:
        model = TituloReceberSdk
        fields = '__all__'
