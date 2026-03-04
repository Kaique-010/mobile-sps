from rest_framework import serializers
from transportes.models import Cte
from transportes.serializers.documento import CteDocumentoSerializer

class CteCompletoSerializer(serializers.ModelSerializer):
    documentos = CteDocumentoSerializer(many=True, read_only=True)
    
    class Meta:
        model = Cte
        fields = '__all__'
