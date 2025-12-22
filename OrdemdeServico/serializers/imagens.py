import base64
import logging
from datetime import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .base import BancoModelSerializer
from ..models import Ordemservicoimgantes, Ordemservicoimgdurante, Ordemservicoimgdepois

logger = logging.getLogger(__name__)

class ImagemBase64Serializer(BancoModelSerializer):
    imagem_base64 = serializers.SerializerMethodField()
    imagem_data_uri = serializers.SerializerMethodField()
    imagem_upload = serializers.CharField(write_only=True, required=False)

    def validate_img_data(self, value):
        if value and isinstance(value, datetime):
            if value.year < 1900 or value.year > 2100:
                raise ValidationError('Ano da data da imagem deve estar entre 1900 e 2100.')
        return value

    def get_imagem_base64(self, obj):
        campo_imagem = getattr(obj, self.Meta.imagem_field, None)
        if campo_imagem and len(campo_imagem) > 0:
            try:
                return base64.b64encode(campo_imagem).decode('utf-8')
            except Exception as e:
                logger.warning(f"Erro ao codificar imagem: {e}")
        return None

    def get_imagem_data_uri(self, obj):
        campo_imagem = getattr(obj, self.Meta.imagem_field, None)
        if campo_imagem and len(campo_imagem) > 0:
            try:
                b64 = base64.b64encode(campo_imagem).decode('utf-8')
                mime = self._detectar_mime(campo_imagem)
                return f"data:{mime};base64,{b64}"
            except Exception:
                return None
        return None

    def _detectar_mime(self, blob):
        try:
            head = bytes(blob)[:12]
        except Exception:
            return 'image/octet-stream'
        if len(head) >= 3 and head[0] == 0xFF and head[1] == 0xD8 and head[2] == 0xFF:
            return 'image/jpeg'
        if len(head) >= 8 and head[:8] == b"\x89PNG\r\n\x1a\n":
            return 'image/png'
        if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            return 'image/webp'
        return 'image/octet-stream'

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        img_base64 = data.get('imagem_upload')
        if isinstance(img_base64, str) and img_base64.strip():
            try:
                texto = img_base64.strip()
                if ',' in texto:
                    texto = texto.split(',', 1)[1]
                ret[self.Meta.imagem_field] = base64.b64decode(texto)
            except Exception as e:
                logger.warning(f"Erro ao decodificar imagem base64: {e}")
                raise ValidationError({'imagem_upload': 'Imagem inválida ou corrompida.'})
        ret.pop('imagem_upload', None)
        return ret

class OrdemServicoImgAntesSerializer(ImagemBase64Serializer):
    class Meta:
        model = Ordemservicoimgantes
        imagem_field = 'iman_imag'
        fields = [
            'iman_id', 'iman_empr', 'iman_fili', 'iman_orde', 'iman_codi',
            'iman_come', 'iman_obse', 'img_latitude', 'img_longitude',
            'img_data', 'imagem_base64', 'imagem_data_uri', 'imagem_upload'
        ]

class ImagemAntesSerializer(ImagemBase64Serializer):
    class Meta:
        model = Ordemservicoimgantes
        imagem_field = 'iman_imag'
        fields = [
            'iman_id', 'iman_empr', 'iman_fili', 'iman_orde', 'iman_codi',
            'iman_come', 'iman_obse', 'img_latitude', 'img_longitude',
            'img_data', 'imagem_base64', 'imagem_data_uri', 'imagem_upload'
        ]

class ImagemDuranteSerializer(ImagemBase64Serializer):
    class Meta:
        model = Ordemservicoimgdurante
        imagem_field = 'imdu_imag'
        fields = [
            'imdu_id', 'imdu_empr', 'imdu_fili', 'imdu_orde', 'imdu_codi',
            'imdu_come', 'imdu_obse', 'img_latitude', 'img_longitude',
            'img_data', 'imagem_base64', 'imagem_data_uri', 'imagem_upload'
        ]

class ImagemDepoisSerializer(ImagemBase64Serializer):
    class Meta:
        model = Ordemservicoimgdepois
        imagem_field = 'imde_imag'
        fields = [
            'imde_id', 'imde_empr', 'imde_fili', 'imde_orde', 'imde_codi',
            'imde_come', 'imde_obse', 'img_latitude', 'img_longitude',
            'img_data', 'imagem_base64', 'imagem_data_uri', 'imagem_upload'
        ]
