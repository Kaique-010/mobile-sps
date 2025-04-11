from rest_framework import serializers
from .models import Entidades

class EntidadesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entidades
        fields = '__all__'

