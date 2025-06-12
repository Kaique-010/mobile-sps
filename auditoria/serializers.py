from rest_framework import serializers
from .models import LogAcao
from django.contrib.auth import get_user_model

User = get_user_model()

class LogAcaoSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source='usuario.usua_nome', read_only=True)
    acao_descricao = serializers.CharField(source='acao_formatada', read_only=True)
    data_hora_formatada = serializers.SerializerMethodField()

    class Meta:
        model = LogAcao
        fields = [
            'id', 'usuario', 'usuario_nome', 'data_hora', 'data_hora_formatada',
            'tipo_acao', 'acao_descricao', 'url', 'ip', 'navegador',
            'dados', 'empresa', 'licenca'
        ]
        read_only_fields = fields

    def get_data_hora_formatada(self, obj):
        return obj.data_hora.strftime('%d/%m/%Y %H:%M:%S')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Formata os dados para melhor visualização
        if data['dados']:
            if isinstance(data['dados'], dict):
                # Remove campos sensíveis ou desnecessários
                data['dados'].pop('password', None)
                data['dados'].pop('senha', None)
        return data