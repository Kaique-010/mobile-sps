from rest_framework import serializers
from Produtos.models import Produtos
from Licencas.models import Usuarios
from coletaestoque.models import ColetaEstoque
from core.utils import get_licenca_db_config

class ColetaEstoqueSerializer(serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField()
    produto_codigo = serializers.CharField(source='cole_prod', read_only=True)
    usuario_nome = serializers.SerializerMethodField()
    
    def get_produto_nome(self, obj):
        try:
            banco = self.context.get('banco')
            produto = Produtos.objects.using(banco).filter(prod_codi=obj.cole_prod).first()
            return produto.prod_nome if produto else None
        except:
            return None
    
    def get_usuario_nome(self, obj):
        try:
            banco = self.context.get('banco')
            usuario = Usuarios.objects.using(banco).filter(usua_codi=obj.cole_usua).first()
            return usuario.usua_nome if usuario else None
        except:
            return None
    
    class Meta:
        model = ColetaEstoque
        fields = '__all__'
        read_only_fields = ('cole_data_leit',)

    def validate_cole_quan_lida(self, value):
        if value <= 0:
            raise serializers.ValidationError("A quantidade lida deve ser maior que zero.")
        return value

    def create(self, validated_data):
        # Os valores de cole_empr e cole_fili já vêm corretos do validated_data
        # Não precisamos sobrescrever com banco ou empresa_id do contexto
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Os valores de cole_empr e cole_fili já vêm corretos do validated_data
        # Não precisamos sobrescrever com banco ou empresa_id do contexto
        return super().update(instance, validated_data)
    