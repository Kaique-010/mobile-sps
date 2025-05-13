from rest_framework.response import Response
from rest_framework import serializers
from rest_framework import status
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
        # Se não veio PK, autogerar
        if 'enti_clie' not in validated_data or validated_data['enti_clie'] is None:
            max_enti = Entidades.objects.aggregate(Max('enti_clie'))['enti_clie__max'] or 0
            validated_data['enti_clie'] = max_enti + 1
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Garante que o campo sequencial não seja modificado no update
        validated_data.pop('enti_clie', None)
        return super().update(instance, validated_data)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['enti_fant'].required = False

    def get_empresa_nome(self, obj):
        try:
            if obj and obj.enti_empr is not None:
                return Empresas.objects.get(empr_codi=obj.enti_empr).empr_nome
        except Empresas.DoesNotExist:
            return None
        return None

    def validate_enti_clie(self, value):
        if value == '':
            raise serializers.ValidationError("Código da entidade não pode ser vazio.")
        return value
    
    def validate_enti_fili(self, value):
        # Adiciona a validação de preenchimento para `enti_fili`
        if value == '':
            return None  # Não salva vazio, trata como `None`
        return value

    def to_representation(self, instance):
        try:
            ret = super().to_representation(instance)
            
            campos_inteiros = ['enti_clie', 'enti_empr']
            for field in campos_inteiros:
                if ret.get(field) == '':
                    ret[field] = None

            return ret
        except Exception as e:
            campos_inteiros = ['enti_clie', 'enti_empr']
            for field in campos_inteiros:
                try:
                    valor = getattr(instance, field, None)
                    self.fields[field].to_representation(valor)
                except Exception as inner_e:
                    print(f"\n❌ Erro no campo: {field}")
                    print(f"👉 Valor: {valor!r}")
                    print(f"💥 Erro: {inner_e}")
                    break
            raise e  # Relevanta o erro original depois de logar
