from rest_framework import serializers
from .models import LicencaWeb


class LicencaWebSerializer(serializers.ModelSerializer):
    class Meta:
        model = LicencaWeb
        fields = (
            'slug', 'cnpj', 'db_name', 'db_host', 'db_port', 'modulos'
        )

