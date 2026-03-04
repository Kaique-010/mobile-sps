from rest_framework import serializers
from transportes.models import CteDocumento

class CteDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CteDocumento
        fields = '__all__'
