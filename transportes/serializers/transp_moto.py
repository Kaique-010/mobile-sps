from rest_framework import serializers

from Entidades.models import Entidades


class TranspMotoSerializer(serializers.ModelSerializer):
    codigo = serializers.IntegerField(source='enti_clie', read_only=True)
    nome = serializers.CharField(source='enti_nome')
    fantasia = serializers.CharField(source='enti_fant', allow_blank=True, allow_null=True, required=False)
    tipo = serializers.CharField(source='enti_tien')
    situacao = serializers.CharField(source='enti_situ')
    email = serializers.CharField(source='enti_emai', allow_blank=True, allow_null=True, required=False)
    telefone = serializers.CharField(source='enti_fone', allow_blank=True, allow_null=True, required=False)
    celular = serializers.CharField(source='enti_celu', allow_blank=True, allow_null=True, required=False)
    cep = serializers.CharField(source='enti_cep')
    endereco = serializers.CharField(source='enti_ende')
    numero = serializers.CharField(source='enti_nume')
    bairro = serializers.CharField(source='enti_bair')
    cidade = serializers.CharField(source='enti_cida')
    estado = serializers.CharField(source='enti_esta')
    complemento = serializers.CharField(source='enti_comp', allow_blank=True, allow_null=True, required=False)

    class Meta:
        model = Entidades
        fields = [
            'codigo', 'nome', 'fantasia', 'tipo', 'situacao',
            'telefone', 'celular', 'email',
            'cep', 'endereco', 'numero', 'bairro', 'cidade', 'estado', 'complemento',
        ]

    def update(self, instance, validated_data):
        using = self.context.get('using')
        for source_field, value in validated_data.items():
            setattr(instance, source_field, value)
        if using:
            instance.save(using=using)
        else:
            instance.save()
        return instance
