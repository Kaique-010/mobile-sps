from rest_framework import serializers
from Entidades.models import Entidades
from ..models import Adiantamentos


class AdiantamentosSerializer(serializers.ModelSerializer):
    entidade_nome = serializers.SerializerMethodField()

    class Meta:
        model = Adiantamentos
        fields = '__all__'
        extra_kwargs = {
            'adia_valo': {'required': False},
            'adia_util': {'required': False},
            'adia_sald': {'required': False},
        }

    def get_entidade_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            entidade = Entidades.objects.using(banco).filter(
                enti_clie=obj.adia_enti,
                enti_empr=obj.adia_empr,
            ).first()
            return entidade.enti_nome if entidade else None
        except Exception:
            return None

    def validate(self, data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError('Banco não encontrado')

        erros = {}
        obrigatorios = [
            'adia_tipo',
            'adia_valo',
            'adia_enti',
            'adia_docu',
            'adia_seri',
        ]

        for campo in obrigatorios:
            if not data.get(campo):
                erros[campo] = ['Este campo é obrigatório.']

        if erros:
            raise serializers.ValidationError(erros)

        return data

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError('Banco não encontrado')

        from ..services import AdiantamentosService

        adiantamento = AdiantamentosService.criar_adiantamento(
            dados=validated_data,
            using=banco,
        )
        return adiantamento

    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError('Banco não encontrado')

        from ..services import AdiantamentosService

        return AdiantamentosService.update(
            instance,
            validated_data,
            using=banco,
        )
