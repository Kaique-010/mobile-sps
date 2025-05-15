from rest_framework import serializers
from .models import LicencaGlobal

class LicencaGlobalSerializer(serializers.ModelSerializer):
    class Meta:
        model = LicencaGlobal
        fields = '__all__'
