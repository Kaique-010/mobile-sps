from rest_framework import serializers
from django.db.models import Max
from .models import Entidades
from Licencas.models  import Empresas

class EntidadesSerializer(serializers.ModelSerializer):
    
    empresa_nome = serializers.SerializerMethodField()
    class Meta:
        model = Entidades
        fields = '__all__'

    def validate(self, data):
        erros = {}
        obrigatorios = ['enti_nome', 'enti_cep', 'enti_ende', 'enti_nume', 'enti_cida', 'enti_esta']

        for campo in obrigatorios:
            if not data.get(campo):
                erros[campo] = ['Este Campo é Obrigatório.']

        
        enti_clie = data.get('enti_clie')
        if enti_clie:
            if Entidades.objects.filter(enti_clie=enti_clie).exists():
                erros['enti_clie'] = ['Este código já existe.']

        if erros:
            raise serializers.ValidationError(erros)

        return data

    def create(self, validated_data):
        if not validated_data.get('enti_clie'):
            max_enti = Entidades.objects.aggregate(Max('enti_clie'))['enti_clie__max'] or 0
            validated_data['enti_clie'] = max_enti + 1

        return super().create(validated_data)      
        
    
    
    def update(self, instance, validated_data):
        # Garante que o campo sequencial não seja modificado no update
        validated_data.pop('enti_clie', None)
        return super().update(instance, validated_data)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['enti_clie'].required = False
        self.fields['enti_fant'].required = False

    def get_empresa_nome(self, obj):
        try:
            return Empresas.objects.get(empr_codi=obj.enti_empr).empr_nome
        except Empresas.DoesNotExist:
            return None