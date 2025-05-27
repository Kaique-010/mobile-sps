from rest_framework import serializers
from .models import Contratosvendas


class ContratosvendasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contratosvendas
        fields = '__all__'