import base64
import logging
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from core.serializers import BancoContextMixin
from .models import (
    Ordemservico, Ordemservicopecas, Ordemservicoservicos,
    Ordemservicoimgantes, Ordemservicoimgdurante, Ordemservicoimgdepois
)

logger = logging.getLogger(__name__)



class BancoModelSerializer(BancoContextMixin, serializers.ModelSerializer):
    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError('Banco não encontrado no contexto')
        return self.Meta.model.objects.using(banco).create(**validated_data)

    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError('Banco não encontrado no contexto')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)
        return instance


# Serializer de Ordem de Serviço
class OrdemServicoSerializer(BancoModelSerializer):
    class Meta:
        model = Ordemservico
        fields = '__all__'

VALID_STATUSES = [0, 1, 2, 3, 4, 5, 20]

def validate_orde_stat(self, value):
    if value not in self.VALID_STATUSES:
        raise ValidationError('Status inválido.')
    return value


class OrdemServicoPecasSerializer(BancoModelSerializer):
    class Meta:
        model = Ordemservicopecas
        fields = '__all__'



class OrdemServicoServicosSerializer(BancoModelSerializer):
    class Meta:
        model = Ordemservicoservicos
        fields = '__all__'



class ImagemBase64Serializer(BancoModelSerializer):
    imagem_base64 = serializers.SerializerMethodField()
    imagem_upload = serializers.CharField(write_only=True, required=False)

    def get_imagem_base64(self, obj):
        campo_imagem = getattr(obj, self.Meta.imagem_field, None)
        if campo_imagem and len(campo_imagem) > 0:
            try:
                return base64.b64encode(campo_imagem).decode('utf-8')
            except Exception as e:
                logger.warning(f"Erro ao codificar imagem: {e}")
        return None

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        img_base64 = data.get('imagem_upload')
        if isinstance(img_base64, str) and img_base64.strip():
            try:
                ret[self.Meta.imagem_field] = base64.b64decode(img_base64)
            except Exception as e:
                logger.warning(f"Erro ao decodificar imagem base64: {e}")
                raise ValidationError({'imagem_upload': 'Imagem inválida ou corrompida.'})
        return ret



class ImagemAntesSerializer(ImagemBase64Serializer):
    class Meta:
        model = Ordemservicoimgantes
        imagem_field = 'iman_imag'
        fields = [
            'iman_id', 'iman_empr', 'iman_fili', 'iman_orde', 'iman_codi',
            'iman_come', 'iman_obse', 'img_latitude', 'img_longitude',
            'img_data', 'imagem_base64', 'imagem_upload'
        ]


# Imagem Durante
class ImagemDuranteSerializer(ImagemBase64Serializer):
    class Meta:
        model = Ordemservicoimgdurante
        imagem_field = 'imdu_imag'
        fields = [
            'imdu_id', 'imdu_empr', 'imdu_fili', 'imdu_orde', 'imdu_codi',
            'imdu_come', 'imdu_obse', 'img_latitude', 'img_longitude',
            'img_data', 'imagem_base64', 'imagem_upload'
        ]


# Imagem Depois
class ImagemDepoisSerializer(ImagemBase64Serializer):
    class Meta:
        model = Ordemservicoimgdepois
        imagem_field = 'imde_imag'
        fields = [
            'imde_id', 'imde_empr', 'imde_fili', 'imde_orde', 'imde_codi',
            'imde_come', 'imde_obse', 'img_latitude', 'img_longitude',
            'img_data', 'imagem_base64', 'imagem_upload'
        ]
