from .models import EntidadesFaces
from rest_framework import serializers


class EntidadesFacesSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntidadesFaces
        fields = '__all__'
        read_only_fields = ['face_enti']
    
class FaceInputSerializer(serializers.Serializer):
    image = serializers.CharField()