
import base64

from django.db import models
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.serializers import BancoContextMixin
from core.db_columns import campo_existe_no_banco

from ..models import Osexterna, Servicososexterna
from Entidades.models import Entidades


class Base64BinaryField(serializers.Field):

    def to_representation(self, value):
        if value is None:
            return None

        if isinstance(value, memoryview):
            value = value.tobytes()

        if isinstance(value, bytes):
            try:
                decoded_str = value.decode('utf-8')

                if decoded_str.startswith('data:image/'):
                    return decoded_str.split('base64,', 1)[1]

            except Exception:
                pass

            return base64.b64encode(value).decode()

        if isinstance(value, str):

            if value.startswith('data:image/'):
                try:
                    return value.split('base64,', 1)[1]
                except Exception:
                    return value

            try:
                decoded = base64.b64decode(value)
                decoded_str = decoded.decode('utf-8')

                if decoded_str.startswith('data:image/'):
                    return decoded_str.split('base64,', 1)[1]

            except Exception:
                pass

            return value

        try:
            return base64.b64encode(str(value).encode()).decode()
        except Exception:
            return None

    def to_internal_value(self, data):
        if not data:
            return None

        if isinstance(data, str) and "base64," in data:
            data = data.split("base64,", 1)[1]

        try:
            return base64.b64decode(data)
        except Exception:
            return data


class BancoModelSerializer(
    BancoContextMixin,
    serializers.ModelSerializer
):

    def _get_banco(self):
        banco = self.context.get("banco")

        if not banco:
            raise ValidationError("Banco não encontrado no contexto")

        return banco

    def _campo_existe(self, campo, banco):
        return campo_existe_no_banco(
            model=self.Meta.model,
            field_name=campo,
            using=banco
        )

    def create(self, validated_data):
        banco = self._get_banco()

        return self.Meta.model.objects.using(banco).create(
            **validated_data
        )

    def update(self, instance, validated_data):
        banco = self._get_banco()

        campos_update = []

        for campo, valor in validated_data.items():

            if not self._campo_existe(campo, banco):
                continue

            field = self.Meta.model._meta.get_field(campo)

            setattr(instance, field.attname, valor)

            campos_update.append(field.name)

        if campos_update:
            instance.save(
                using=banco,
                update_fields=campos_update
            )

        return instance


class ServicososexternaSerializer(BancoModelSerializer):

    class Meta:
        model = Servicososexterna
        fields = "__all__"

    def to_representation(self, obj):
        data = super().to_representation(obj)

        # Compatibilidade com o frontend.
        data['serv_unit'] = data.get('serv_valo_unit')
        data['serv_tota'] = data.get('serv_valo_tota')

        return data

    def create(self, validated_data):

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

    servicos = ServicososexternaSerializer(
        many=True,
        required=False
    )

    cliente_nome = serializers.SerializerMethodField()
    responsavel_nome = serializers.SerializerMethodField()

    osex_assi_clie = Base64BinaryField(
        required=False,
        allow_null=True
    )

    osex_assi_oper = Base64BinaryField(
        required=False,
        allow_null=True
    )

    class Meta:
        model = Osexterna
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)

        banco = self.context.get('banco')

        if banco:
            qs = (
                Servicososexterna.objects.using(banco)
                .filter(
                    serv_empr=instance.osex_empr,
                    serv_fili=instance.osex_fili,
                    serv_os=instance.osex_codi
                )
                .order_by('serv_sequ')
            )

            data['servicos'] = ServicososexternaSerializer(
                qs,
                many=True,
                context=self.context
            ).data

        return data

    def get_cliente_nome(self, obj):
        banco = self.context.get('banco')

        if not obj.osex_clie or not banco:
            return None

        cli = (
            Entidades.objects.using(banco)
            .filter(
                enti_clie=obj.osex_clie,
                enti_empr=obj.osex_empr
            )
            .first()
        )

        return getattr(cli, 'enti_nome', None)

    def get_responsavel_nome(self, obj):
        banco = self.context.get('banco')

        if not obj.osex_resp or not banco:
            return None

        resp = (
            Entidades.objects.using(banco)
            .filter(
                enti_clie=obj.osex_resp,
                enti_empr=obj.osex_empr
            )
            .first()
        )

        return getattr(resp, 'enti_nome', None)

    def create(self, validated_data):
        servicos = validated_data.pop('servicos', [])

        osex = super().create(validated_data)

        self._sync_servicos(osex, servicos)
        self._recalcular_total(osex)

        return osex

    def update(self, instance, validated_data):
        servicos = validated_data.pop('servicos', None)

        instance = super().update(instance, validated_data)

        if servicos is not None:
            self._clear_servicos(instance)
            self._sync_servicos(instance, servicos)

        self._recalcular_total(instance)

        return instance

    def _clear_servicos(self, osex):
        banco = self._get_banco()

        (
            Servicososexterna.objects.using(banco)
            .filter(
                serv_empr=osex.osex_empr,
                serv_fili=osex.osex_fili,
                serv_os=osex.osex_codi
            )
            .delete()
        )

    def _sync_servicos(self, osex, servicos_list):
        banco = self._get_banco()

        last_seq = (
            Servicososexterna.objects.using(banco)
            .filter(
                serv_empr=osex.osex_empr,
                serv_fili=osex.osex_fili,
                serv_os=osex.osex_codi
            )
            .aggregate(
                models.Max('serv_sequ')
            )['serv_sequ__max'] or 0
        )

        seq = last_seq

        for item in servicos_list or []:
            seq += 1

            unit = (
                item.get('serv_valo_unit')
                or item.get('serv_unit')
                or 0
            )

            quan = item.get('serv_quan') or 0

            tota = (
                item.get('serv_valo_tota')
                or item.get('serv_tota')
                or (float(unit or 0) * float(quan or 0))
            )

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
        banco = self._get_banco()

        total = (
            Servicososexterna.objects.using(banco)
            .filter(
                serv_empr=osex.osex_empr,
                serv_fili=osex.osex_fili,
                serv_os=osex.osex_codi
            )
            .aggregate(
                total=models.Sum('serv_valo_tota')
            )['total'] or 0
        )

        # UPDATE protegido pelo SafeMissingColumnsManager.
        (
            Osexterna.objects.using(banco)
            .filter(
                osex_codi=osex.osex_codi,
                osex_empr=osex.osex_empr,
                osex_fili=osex.osex_fili
            )
            .update(
                osex_valo_tota=total
            )
        )

        osex.osex_valo_tota = total
