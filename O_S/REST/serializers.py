import base64
import logging
from django.db import models
from datetime import datetime, timedelta
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from Entidades.models import Entidades
from Produtos.models import Produtos
from contas_a_receber.models import Titulosreceber
from core.serializers import BancoContextMixin
from ..models import Os, PecasOs, ServicosOs, OsHora, OrdemServicoGeral

logger = logging.getLogger(__name__)

class Base64BinaryField(serializers.Field):
    def to_representation(self, value):
        if not value:
            return None
        try:
            data = value.tobytes() if hasattr(value, 'tobytes') else (bytes(value) if isinstance(value, memoryview) else value)
        except Exception:
            data = value
        return base64.b64encode(data).decode()

    def to_internal_value(self, data):
        return base64.b64decode(data) if data else None


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

class OsHoraSerializer(BancoModelSerializer):
    total_horas = serializers.SerializerMethodField()
    operador_nome = serializers.SerializerMethodField()
    
    class Meta:
        model = OsHora
        fields = '__all__'
    
    def get_total_horas(self, obj):
        """Calcula total de horas trabalhadas"""
        total = 0.0
        
        # Manhã
        if obj.os_hora_manh_ini and obj.os_hora_manh_fim:
            ini = datetime.combine(datetime.today(), obj.os_hora_manh_ini)
            fim = datetime.combine(datetime.today(), obj.os_hora_manh_fim)
            total += (fim - ini).total_seconds() / 3600
        
        # Tarde
        if obj.os_hora_tard_ini and obj.os_hora_tard_fim:
            ini = datetime.combine(datetime.today(), obj.os_hora_tard_ini)
            fim = datetime.combine(datetime.today(), obj.os_hora_tard_fim)
            total += (fim - ini).total_seconds() / 3600
        
        return round(total, 2)
    
    def get_operador_nome(self, obj):
        """Retorna nome do operador"""
        if not obj.os_hora_oper:
            return None
        banco = self.context.get('banco')
        try:
            from Entidades.models import Entidades
            oper = Entidades.objects.using(banco).get(
                enti_func=obj.os_hora_oper,
                enti_empr=obj.os_hora_empr
            )
            return oper.enti_nome
        except:
            return None
    
    def validate(self, data):
        """Validações customizadas"""
        # Valida horários da manhã
        if data.get('os_hora_manh_ini') and data.get('os_hora_manh_fim'):
            if data['os_hora_manh_ini'] >= data['os_hora_manh_fim']:
                raise ValidationError("Horário de início deve ser menor que fim (manhã)")
        
        # Valida horários da tarde
        if data.get('os_hora_tard_ini') and data.get('os_hora_tard_fim'):
            if data['os_hora_tard_ini'] >= data['os_hora_tard_fim']:
                raise ValidationError("Horário de início deve ser menor que fim (tarde)")
        
        # Valida KM
        if data.get('os_hora_km_sai') and data.get('os_hora_km_che'):
            if data['os_hora_km_sai'] > data['os_hora_km_che']:
                raise ValidationError("KM de saída não pode ser maior que chegada")
        
        return data



class ItemOsBaseSerializer(BancoModelSerializer):
    codigo_field = None       # peca_prod / serv_prod
    prefix = None             # peca / serv
    model_class = None

    class Meta:
        fields = "__all__"

    # Valida base
    def validate(self, data):
        obrig = [
            f"{self.prefix}_empr",
            f"{self.prefix}_fili",
            f"{self.prefix}_os",
            self.codigo_field,
        ]

        for campo in obrig:
            if not data.get(campo):
                raise ValidationError(f"O campo {campo} é obrigatório.")

        # total calculado
        q = data.get(f"{self.prefix}_quan", 0)
        u = data.get(f"{self.prefix}_unit", 0)
        if q < 0 or u < 0:
            raise ValidationError("Quantidade/Valor não podem ser negativos.")

        data[f"{self.prefix}_tota"] = q * u
        return data

    # valida se produto existe
    def validate_codigo(self, value):
        banco = self.context.get("banco")
        if banco and not Produtos.objects.using(banco).filter(prod_codi=value).exists():
            raise ValidationError("Produto não encontrado.")
        return value

    def create(self, validated_data):
        banco = self.context.get("banco")
        return self.model_class.objects.using(banco).create(**validated_data)



class PecasOsSerializer(ItemOsBaseSerializer):
    codigo_field = "peca_prod"
    prefix = "peca"
    model_class = PecasOs

    produto_nome = serializers.SerializerMethodField()

    class Meta:
        model = PecasOs
        fields = "__all__"

    def get_produto_nome(self, obj):
        banco = self.context.get("banco")
        try:
            prod = Produtos.objects.using(banco).get(prod_codi=obj.peca_prod)
            return prod.prod_nome
        except:
            return ""



class ServicosOsSerializer(ItemOsBaseSerializer):
    codigo_field = "serv_prod"
    prefix = "serv"
    model_class = ServicosOs

    class Meta:
        model = ServicosOs
        fields = "__all__"




class OsSerializer(BancoModelSerializer):
    pecas = PecasOsSerializer(many=True, required=False)
    servicos = ServicosOsSerializer(many=True, required=False)
    horas = OsHoraSerializer(many=True, required=False)
    
    cliente_nome = serializers.SerializerMethodField()
    total_pecas = serializers.SerializerMethodField()
    total_servicos = serializers.SerializerMethodField()
    
    # CORRIGIR NOMES DOS CAMPOS DE ASSINATURA
    os_assi_clie = Base64BinaryField(required=False)
    os_assi_oper = Base64BinaryField(required=False)

    class Meta:
        model = Os
        fields = '__all__'

    def get_cliente_nome(self, obj):
        banco = self.context.get("banco")
        if not banco:
            return None
        cli = Entidades.objects.using(banco).filter(
            enti_clie=obj.os_clie,
            enti_empr=obj.os_empr,
        ).first()
        return cli.enti_nome if cli else None
    
    def get_total_pecas(self, obj):
        """Calcula total de peças"""
        banco = self.context.get('banco')
        total = PecasOs.objects.using(banco).filter(
            peca_empr=obj.os_empr,
            peca_fili=obj.os_fili,
            peca_os=obj.os_os
        ).aggregate(total=models.Sum('peca_tota'))['total'] or 0
        return float(total)
    
    def get_total_servicos(self, obj):
        """Calcula total de serviços"""
        banco = self.context.get('banco')
        total = ServicosOs.objects.using(banco).filter(
            serv_empr=obj.os_empr,
            serv_fili=obj.os_fili,
            serv_os=obj.os_os
        ).aggregate(total=models.Sum('serv_tota'))['total'] or 0
        return float(total)

    def create(self, validated_data):
        pecas = validated_data.pop("pecas", [])
        servs = validated_data.pop("servicos", [])
        horas = validated_data.pop("horas", [])
        
        os_obj = super().create(validated_data)
        
        self._sync_items(os_obj, PecasOs, "peca", pecas)
        self._sync_items(os_obj, ServicosOs, "serv", servs)
        self._sync_items(os_obj, OsHora, "os_hora", horas)
        
        return os_obj

    def update(self, instance, validated_data):
        pecas = validated_data.pop("pecas", [])
        servs = validated_data.pop("servicos", [])
        horas = validated_data.pop("horas", [])
        
        instance = super().update(instance, validated_data)
        
        self._sync_items(instance, PecasOs, "peca", pecas)
        self._sync_items(instance, ServicosOs, "serv", servs)
        self._sync_items(instance, OsHora, "os_hora", horas)
        
        return instance

    def _sync_items(self, os_obj, model, prefix, data_list):
        """Sincroniza itens relacionados"""
        banco = self.context.get("banco")
        ids = []
        
        for item in data_list:
            item[f"{prefix}_empr"] = os_obj.os_empr
            item[f"{prefix}_fili"] = os_obj.os_fili
            item[f"{prefix}_os"] = os_obj.os_os

            pk = item.get(f"{prefix}_item")
            if pk:
                obj, _ = model.objects.using(banco).update_or_create(
                    **{
                        f"{prefix}_item": pk,
                        f"{prefix}_empr": os_obj.os_empr,
                        f"{prefix}_fili": os_obj.os_fili,
                        f"{prefix}_os": os_obj.os_os,
                    },
                    defaults=item,
                )
            else:
                obj = model.objects.using(banco).create(**item)

            ids.append(getattr(obj, f"{prefix}_item"))

        # Remove itens deletados
        model.objects.using(banco).filter(
            **{f"{prefix}_os": os_obj.os_os}
        ).exclude(
            **{f"{prefix}_item__in": ids}
        ).delete()




class TituloReceberSerializer(BancoModelSerializer):
    class Meta:
        model = Titulosreceber
        fields = [
            'titu_empr',
            'titu_fili',
            'titu_titu',
            'titu_seri',
            'titu_parc',
            'titu_clie',
            'titu_valo',
            'titu_venc',
            'titu_form_reci',
        ]





class OrdemServicoGeralSerializer(BancoModelSerializer):
    class Meta:
        model = OrdemServicoGeral
        fields = '__all__'
