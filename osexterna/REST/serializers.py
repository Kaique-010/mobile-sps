from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.db import models
from core.serializers import BancoContextMixin
from ..models import Osexterna, Servicososexterna
from Entidades.models import Entidades
import base64


class Base64BinaryField(serializers.Field):
    def to_representation(self, value):
        if value is None:
            return None
        # DB pode retornar memoryview/bytes/texto
        if isinstance(value, memoryview):
            value = value.tobytes()
        if isinstance(value, bytes):
            # Se bytes representarem uma data URL, extrair base64
            try:
                decoded_str = value.decode('utf-8')
                if decoded_str.startswith('data:image/'):
                    try:
                        return decoded_str.split('base64,', 1)[1]
                    except Exception:
                        return decoded_str
            except Exception:
                pass
            return base64.b64encode(value).decode()
        if isinstance(value, str):
            # Caso já esteja como data URL
            if value.startswith('data:image/'):
                try:
                    return value.split('base64,', 1)[1]
                except Exception:
                    return value
            # Caso seja base64 que ao decodificar vira data URL
            try:
                decoded = base64.b64decode(value)
                decoded_str = None
                try:
                    decoded_str = decoded.decode('utf-8')
                except Exception:
                    decoded_str = None
                if decoded_str and decoded_str.startswith('data:image/'):
                    return decoded_str.split('base64,', 1)[1]
            except Exception:
                pass
            # Caso seja base64 puro da imagem
            return value
        # Fallback
        try:
            return base64.b64encode(str(value).encode()).decode()
        except Exception:
            return None

    def to_internal_value(self, data):
        if not data:
            return None
        # Aceitar tanto data URL quanto base64 puro
        if isinstance(data, str) and "base64," in data:
            data = data.split("base64,", 1)[1]
        try:
            return base64.b64decode(data)
        except Exception:
            # Se não for base64 válido, armazena como texto
            return data





class BancoModelSerializer(BancoContextMixin, serializers.ModelSerializer):
    def create(self, validated_data):
        banco = self.context.get("banco")
        if not banco:
            raise ValidationError("Banco não encontrado no contexto")
        return self.Meta.model.objects.using(banco).create(**validated_data)

    def update(self, instance, validated_data):
        banco = self.context.get("banco")
        if not banco:
            raise ValidationError("Banco não encontrado no contexto")
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save(using=banco)
        return instance

class ServicososexternaSerializer(BancoModelSerializer):
    class Meta:
        model = Servicososexterna
        fields = "__all__"

    def to_representation(self, obj):
        data = super().to_representation(obj)
        # compatibilidade com front: expor serv_unit/serv_tota
        data['serv_unit'] = data.get('serv_valo_unit')
        data['serv_tota'] = data.get('serv_valo_tota')
        return data

    def create(self, validated_data):
        # compatibilidade com front: aceitar serv_unit/serv_tota
        unit = validated_data.pop('serv_unit', None)
        tota = validated_data.pop('serv_tota', None)
        if unit is not None:
            validated_data['serv_valo_unit'] = unit
        if tota is not None:
            validated_data['serv_valo_tota'] = tota
        return super().create(validated_data)

    def update(self, instance, validated_data):
        unit = validated_data.pop('serv_unit', None)
        tota = validated_data.pop('serv_tota', None)
        if unit is not None:
            validated_data['serv_valo_unit'] = unit
        if tota is not None:
            validated_data['serv_valo_tota'] = tota
        return super().update(instance, validated_data)

class OsexternaSerializer(BancoModelSerializer):
    servicos = ServicososexternaSerializer(many=True, required=False)
    cliente_nome = serializers.SerializerMethodField()
    responsavel_nome = serializers.SerializerMethodField()
    # Assinaturas com normalização flexível (data URL, base64 puro ou bytes)
    osex_assi_clie = Base64BinaryField(required=False, allow_null=True)
    osex_assi_oper = Base64BinaryField(required=False, allow_null=True)

    class Meta:
        model = Osexterna
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        banco = self.context.get('banco')
        if banco:
            qs = Servicososexterna.objects.using(banco).filter(
                serv_empr=instance.osex_empr,
                serv_fili=instance.osex_fili,
                serv_os=instance.osex_codi
            ).order_by('serv_sequ')
            data['servicos'] = ServicososexternaSerializer(qs, many=True, context=self.context).data
        return data

    def get_cliente_nome(self, obj):
        banco = self.context.get('banco')
        if not obj.osex_clie:
            return None
        cli = Entidades.objects.using(banco).filter(
            enti_clie=obj.osex_clie,
            enti_empr=obj.osex_empr
        ).first()
        return getattr(cli, 'enti_nome', None)

    def get_responsavel_nome(self, obj):
        banco = self.context.get('banco')
        if not obj.osex_resp:
            return None
        resp = Entidades.objects.using(banco).filter(
            enti_clie=obj.osex_resp,
            enti_empr=obj.osex_empr
        ).first()
        return getattr(resp, 'enti_nome', None)

    def create(self, validated_data):
        servicos = validated_data.pop('servicos', [])
        osex = super().create(validated_data)
        self._sync_servicos(osex, servicos)
        self._recalcular_total(osex)
        return osex

    def update(self, instance, validated_data):
        servicos = validated_data.pop('servicos', [])
        instance = super().update(instance, validated_data)
        if servicos:
            self._clear_servicos(instance)
            self._sync_servicos(instance, servicos)
        self._recalcular_total(instance)
        return instance

    def _clear_servicos(self, osex):
        banco = self.context.get('banco')
        Servicososexterna.objects.using(banco).filter(
            serv_empr=osex.osex_empr,
            serv_fili=osex.osex_fili,
            serv_os=osex.osex_codi,
        ).delete()

    def _sync_servicos(self, osex, servicos_list):
        banco = self.context.get('banco')
        # obter próximo sequencial por OS
        last_seq = (Servicososexterna.objects.using(banco)
                    .filter(serv_empr=osex.osex_empr, serv_fili=osex.osex_fili, serv_os=osex.osex_codi)
                    .aggregate(models.Max('serv_sequ'))['serv_sequ__max'] or 0)
        seq = last_seq
        for item in (servicos_list or []):
            seq += 1
            unit = item.get('serv_valo_unit') or item.get('serv_unit') or 0
            quan = item.get('serv_quan') or 0
            tota = item.get('serv_valo_tota') or item.get('serv_tota') or (float(unit or 0) * float(quan or 0))
            Servicososexterna.objects.using(banco).create(
                serv_empr=osex.osex_empr,
                serv_fili=osex.osex_fili,
                serv_os=osex.osex_codi,
                serv_sequ=seq,
                serv_desc=item.get('serv_desc') or '',
                serv_quan=quan,
                serv_valo_unit=unit,
                serv_valo_tota=tota,
            )

    def _recalcular_total(self, osex):
        banco = self.context.get('banco')
        total = Servicososexterna.objects.using(banco).filter(
            serv_empr=osex.osex_empr,
            serv_fili=osex.osex_fili,
            serv_os=osex.osex_codi,
        ).aggregate(total=models.Sum('serv_valo_tota'))['total'] or 0
        osex.osex_valo_tota = total
        osex.save(using=banco)
