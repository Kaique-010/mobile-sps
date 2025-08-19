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
        read_only_fields = ['enti_clie']

    def validate(self, data):
        
        banco  = self.context.get ('banco')
        
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        
        erros = {}
        obrigatorios = ['enti_nome', 'enti_cep', 'enti_ende', 'enti_nume', 'enti_cida', 'enti_esta']

        for campo in obrigatorios:
            if not data.get(campo):
                erros[campo] = ['Este Campo é Obrigatório.']

        
        if 'enti_clie' in data:
            if Entidades.objects.using(banco).filter(enti_clie=data['enti_clie']).exists():
                erros['enti_clie'] = ['Este código já existe.']

        if erros:
            raise serializers.ValidationError(erros)

        return data

    def create(self, validated_data):
        banco = self.context.get('banco')
        
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        
        
        if not validated_data.get('enti_clie'):
            max_enti = Entidades.objects.using(banco).aggregate(Max('enti_clie'))['enti_clie__max'] or 0
            validated_data['enti_clie'] = max_enti + 1
        return Entidades.objects.using(banco).create(**validated_data)
    
    
    
    def update(self, instance, validated_data):
        
        validated_data.pop('enti_clie', None)
        return super().update(instance, validated_data)

    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['enti_fant'].required = False

    
    def get_empresa_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None
        try:
            if obj and obj.enti_empr is not None:
                empresa = Empresas.objects.using(banco).filter(empr_codi=obj.enti_empr).first()
                return empresa.empr_nome if empresa else None
        except Exception as e:
            return None
        return None




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

