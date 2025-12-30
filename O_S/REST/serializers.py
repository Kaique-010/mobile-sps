import base64
import logging
from django.db import models, IntegrityError, InternalError
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
        if value is None:
            return None
        # DB pode retornar memoryview/bytes/texto
        if isinstance(value, memoryview):
            value = value.tobytes()
        if isinstance(value, bytes):
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

class OsHoraSerializer(BancoModelSerializer):
    total_horas = serializers.SerializerMethodField()
    operador_nome = serializers.SerializerMethodField()
    
    class Meta:
        model = OsHora
        fields = [
            'os_hora_empr',
            'os_hora_fili',
            'os_hora_os',
            'os_hora_item',
            'os_hora_data',
            'os_hora_manh_ini',
            'os_hora_manh_fim',
            'os_hora_tard_ini',
            'os_hora_tard_fim',
            'os_hora_tota',
            'os_hora_km_sai',
            'os_hora_km_che',
            'os_hora_oper',
            'os_hora_equi',
            'os_hora_obse',
            'total_horas',
            'operador_nome',
        ]
    
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
    
class ItemOsBaseSerializer(BancoModelSerializer):
    codigo_field = None       # peca_prod / serv_prod
    prefix = None             # peca / serv
    model_class = None

    class Meta:
        fields = "__all__"

    # Valida base
    def validate(self, data):
        # Validação de campos obrigatórios apenas na criação
        if not self.instance:
            obrig = [
                f"{self.prefix}_empr",
                f"{self.prefix}_fili",
                f"{self.prefix}_os",
                self.codigo_field,
            ]

            for campo in obrig:
                if not data.get(campo):
                    raise ValidationError(f"O campo {campo} é obrigatório.")

        # Recupera valores para cálculo do total (usa instance se parcial)
        def get_val(field_name, default=0):
            val = data.get(field_name)
            if val is not None:
                return val
            if self.instance:
                return getattr(self.instance, field_name, default)
            return default

        q = get_val(f"{self.prefix}_quan")
        u = get_val(f"{self.prefix}_unit")

        if q < 0 or u < 0:
            raise ValidationError("Quantidade/Valor não podem ser negativos.")

        # Recalcula total apenas se houver mudança ou criação
        # Mas como q e u já consideram o valor atual, sempre recalculamos para garantir consistência
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
    
    # Allow UUIDs for offline sync
    peca_item = serializers.CharField(required=False)

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

    def create(self, validated_data):
        if not validated_data.get('peca_data'):
            banco = self.context.get("banco")
            try:
                os_obj = Os.objects.using(banco).get(
                    os_empr=validated_data.get('peca_empr'),
                    os_fili=validated_data.get('peca_fili'),
                    os_os=validated_data.get('peca_os')
                )
                validated_data['peca_data'] = os_obj.os_data_aber
            except:
                pass
        try:
            return super().create(validated_data)
        except (IntegrityError, InternalError) as e:
            if 'Não é permitido estoque negativo' in str(e):
                raise ValidationError(f"Não é permitido estoque negativo para o produto {validated_data.get('peca_prod')}.")
            raise e



class ServicosOsSerializer(ItemOsBaseSerializer):
    codigo_field = "serv_prod"
    prefix = "serv"
    model_class = ServicosOs
    
    # Allow UUIDs for offline sync
    serv_item = serializers.CharField(required=False)

    class Meta:
        model = ServicosOs
        fields = "__all__"




class OsSerializer(BancoModelSerializer):
    pecas = PecasOsSerializer(many=True, required=False)
    servicos = ServicosOsSerializer(many=True, required=False)
    horas = OsHoraSerializer(many=True, required=False)
    
    cliente_nome = serializers.SerializerMethodField()
    cliente_telefone = serializers.SerializerMethodField()
    cliente_celular = serializers.SerializerMethodField()
    total_pecas = serializers.SerializerMethodField()
    total_servicos = serializers.SerializerMethodField()
    total_geral = serializers.SerializerMethodField()
    os_tota = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    
    # CORRIGIR NOMES DOS CAMPOS DE ASSINATURA
    os_assi_clie = Base64BinaryField(required=False)
    os_assi_oper = Base64BinaryField(required=False)
    os_orig = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    # Allow UUID for offline sync
    os_os = serializers.CharField(required=False)
    os_auto = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Os
        fields = '__all__'
        extra_kwargs = {
            'os_os': {'validators': []},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id_mappings = {
            'pecas_ids': [],
            'servicos_ids': [],
            'horas_ids': []
        }

    def get_cliente_nome(self, obj):
        banco = self.context.get("banco")
        if not banco:
            return None
        cli = Entidades.objects.using(banco).filter(
            enti_clie=obj.os_clie,
            enti_empr=obj.os_empr,
        ).first()
        return cli.enti_nome if cli else None

    def get_cliente_telefone(self, obj):
        banco = self.context.get("banco")
        if not banco:
            return None
        cli = Entidades.objects.using(banco).filter(
            enti_clie=obj.os_clie,
            enti_empr=obj.os_empr,
        ).first()
        return cli.enti_fone if cli else None

    def get_cliente_celular(self, obj):
        banco = self.context.get("banco")
        if not banco:
            return None
        cli = Entidades.objects.using(banco).filter(
            enti_clie=obj.os_clie,
            enti_empr=obj.os_empr,
        ).first()
        return cli.enti_celu if cli else None
    
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
    
    def get_total_geral(self, obj):
        """Calcula total geral (pecas + servicos)"""
        return self.get_total_pecas(obj) + self.get_total_servicos(obj)
    

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
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
