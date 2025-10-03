from rest_framework import serializers
from .models import LogAcao
from django.contrib.auth import get_user_model
import json

User = get_user_model()

class LogAcaoSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source='usuario.usua_nome', read_only=True)
    acao_descricao = serializers.CharField(source='acao_formatada', read_only=True)
    data_hora_formatada = serializers.SerializerMethodField()
    tem_alteracoes = serializers.BooleanField(read_only=True)
    resumo_alteracoes = serializers.CharField(read_only=True)
    objeto_info = serializers.CharField(source='get_objeto_info', read_only=True)

    class Meta:
        model = LogAcao
        fields = [
            'id', 'usuario', 'usuario_nome', 'data_hora', 'data_hora_formatada',
            'tipo_acao', 'acao_descricao', 'url', 'ip', 'navegador',
            'dados', 'dados_antes', 'dados_depois', 'campos_alterados',
            'objeto_id', 'modelo', 'objeto_info', 'tem_alteracoes', 'resumo_alteracoes',
            'empresa', 'licenca'
        ]
        read_only_fields = fields

    def get_data_hora_formatada(self, obj):
        return obj.data_hora.strftime('%d/%m/%Y %H:%M:%S')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        # Tentar converter strings JSON para objetos (dict/list)
        for campo_dados in ['dados', 'dados_antes', 'dados_depois', 'campos_alterados']:
            valor = data.get(campo_dados)
            if isinstance(valor, str):
                try:
                    data[campo_dados] = json.loads(valor)
                except (json.JSONDecodeError, TypeError):
                    # Mantém string se não for JSON válido
                    pass
        
        # Remove campos sensíveis de todos os campos de dados
        campos_sensiveis = ['password', 'senha', 'token', 'api_key', 'secret']
        
        for campo_dados in ['dados', 'dados_antes', 'dados_depois']:
            if data.get(campo_dados) and isinstance(data[campo_dados], dict):
                for campo_sensivel in campos_sensiveis:
                    data[campo_dados].pop(campo_sensivel, None)
        
        # Adiciona informação de tipo de alteração baseada no método HTTP
        if data['tipo_acao'] == 'POST':
            data['tipo_alteracao'] = 'Criação'
        elif data['tipo_acao'] in ['PUT', 'PATCH']:
            data['tipo_alteracao'] = 'Atualização'
        elif data['tipo_acao'] == 'DELETE':
            data['tipo_alteracao'] = 'Exclusão'
        elif data['tipo_acao'] == 'GET':
            data['tipo_alteracao'] = 'Consulta'
        else:
            data['tipo_alteracao'] = 'Outro'
        
        return data