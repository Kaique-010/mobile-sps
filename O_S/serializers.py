import base64
import logging
from django.db.models import Max
from django.db import transaction,IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from Entidades.models import Entidades
from contas_a_receber.models import Titulosreceber
from core.serializers import BancoContextMixin
from .models import (
    Os, PecasOs, ServicosOs, OrdemServicoGeral
)

logger = logging.getLogger(__name__)


class BancoModelSerializer(BancoContextMixin, serializers.ModelSerializer):
    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError('Banco não encontrado no contexto')
        instance = self.Meta.model.objects.using(banco).create(**validated_data)
        return instance

    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError('Banco não encontrado no contexto')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)
        return instance


class PecasOsSerializer(BancoModelSerializer):
    peca_item = serializers.IntegerField(required=False)
    peca_empr = serializers.IntegerField(required=True)
    peca_fili = serializers.IntegerField(required=True)
    peca_os = serializers.IntegerField(required=True)
    peca_prod = serializers.CharField(required=True)  # Changed from peca_codi to peca_prod
    peca_comp = serializers.CharField(required=False, allow_blank=True)
    peca_quan = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, default=0)
    peca_unit = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, default=0)
    peca_tota = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, default=0)
    produto_nome = serializers.SerializerMethodField()
   
    class Meta:
        model = PecasOs
        fields = '__all__'
        
    def validate(self, data):
        # Validar campos obrigatórios
        campos_obrigatorios = ['peca_empr', 'peca_fili', 'peca_os', 'peca_prod'] 
        for campo in campos_obrigatorios:
            if campo not in data:
                raise serializers.ValidationError(f"O campo {campo} é obrigatório.")
            
            if data[campo] is None:
                raise serializers.ValidationError(f"O campo {campo} não pode ser nulo.")

        # Validar valores numéricos
        if data.get('peca_quan', 0) < 0:
            raise serializers.ValidationError("A quantidade não pode ser negativa.")
        
        if data.get('peca_unit', 0) < 0:
            raise serializers.ValidationError("O valor unitário não pode ser negativo.")

        # Calcular o total se não fornecido
        if 'peca_tota' not in data and 'peca_quan' in data and 'peca_unit' in data:
            data['peca_tota'] = data['peca_quan'] * data['peca_unit']

        return data

    def validate_peca_quan(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantidade deve ser maior que zero")
        if value > 9999:
            raise serializers.ValidationError("Quantidade muito alta")
        return value
    
    def validate_peca_unit(self, value):
        if value <= 0:
            raise serializers.ValidationError("Valor unitário deve ser maior que zero")
        return value
    
    def validate_peca_prod(self, value):  # Changed from validate_peca_codi to validate_peca_prod
        # Validar se produto existe
        banco = self.context.get('banco')
        if banco:
            from Produtos.models import Produtos
            if not Produtos.objects.using(banco).filter(prod_codi=value).exists():
                raise serializers.ValidationError("Produto não encontrado")
        return value
    
    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco de dados não fornecido.")
      
        return PecasOs.objects.using(banco).create(**validated_data)
    
    
    def get_produto_nome(self, obj):
        try:
            banco = self.context.get('banco')
            from Produtos.models import Produtos

            produto = Produtos.objects.using(banco).get(prod_codi=obj.peca_prod)  # Changed from peca_codi to peca_prod
            return produto.prod_nome
        except:
            return ''


class ServicosOsSerializer(BancoModelSerializer):
    serv_item = serializers.IntegerField(required=False)
    serv_empr = serializers.IntegerField(required=True)
    serv_fili = serializers.IntegerField(required=True)
    serv_os = serializers.IntegerField(required=True)
    serv_prod = serializers.CharField(required=True)
    serv_comp = serializers.CharField(required=False, allow_blank=True)
    serv_quan = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, default=0)
    serv_unit = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, default=0)
    serv_tota = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, default=0)
    
    class Meta:
        model = ServicosOs
        fields = '__all__'
        
    def validate(self, data):
        # Validar campos obrigatórios
        campos_obrigatorios = ['serv_empr', 'serv_fili', 'serv_os', 'serv_prod']
        for campo in campos_obrigatorios:
            if campo not in data:
                raise serializers.ValidationError(f"O campo {campo} é obrigatório.")
            
            if data[campo] is None:
                raise serializers.ValidationError(f"O campo {campo} não pode ser nulo.")

        # Validar valores numéricos
        if data.get('serv_quan', 0) < 0:
            raise serializers.ValidationError("A quantidade não pode ser negativa.")
        
        if data.get('serv_unit', 0) < 0:
            raise serializers.ValidationError("O valor unitário não pode ser negativo.")

        # Calcular o total se não fornecido
        if 'serv_tota' not in data and 'serv_quan' in data and 'serv_unit' in data:
            data['serv_tota'] = data['serv_quan'] * data['serv_unit']

        return data

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco de dados não fornecido.")
        
        return ServicosOs.objects.using(banco).create(**validated_data)


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


class OsSerializer(BancoModelSerializer):
    pecas = PecasOsSerializer(many=True, required=False)
    servicos = serializers.SerializerMethodField()
    cliente_nome = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Os
        fields = '__all__'

    def get_servicos(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return []
        
        servicos = ServicosOs.objects.using(banco).filter(
            serv_empr=obj.os_empr,
            serv_fili=obj.os_fili,
            serv_os=obj.os_os
        ).order_by('serv_item')
        
        return ServicosOsSerializer(servicos, many=True, context=self.context).data
    
    def get_cliente_nome(self, obj):
        banco = self.context.get('banco')
        if not banco or not obj.os_clie or not obj.os_empr:
            return None
            
        try:
            entidade = Entidades.objects.using(banco).get(
                enti_clie=obj.os_clie,
                enti_empr=obj.os_empr
            )
            return entidade.enti_nome
        except Entidades.DoesNotExist:
            logger.warning(f"Entidade não encontrada: empresa {obj.os_empr}, código {obj.os_clie}")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar cliente: {e}")
            return None
            
    def validate_os_stat_os(self, value):
        VALID_STATUSES = [0, 1, 2, 3, 4, 5, 20]
        if value not in VALID_STATUSES:
            raise ValidationError('Status inválido.')
        return value

    def create(self, validated_data):
        pecas_data = validated_data.pop('pecas', [])
        servicos_data = validated_data.pop('servicos', [])
        banco = self.context.get('banco')
        ordem = super().create(validated_data)

        self._sync_pecas(ordem, pecas_data, banco)
        self._sync_servicos(ordem, servicos_data, banco)

        return ordem

    def update(self, instance, validated_data):
        pecas_data = validated_data.pop('pecas', [])
        servicos_data = validated_data.pop('servicos', [])
        banco = self.context.get('banco')

        instance = super().update(instance, validated_data)

        self._sync_pecas(instance, pecas_data, banco)
        self._sync_servicos(instance, servicos_data, banco)

        return instance

    def _sync_pecas(self, ordem, pecas_data, banco):
        ids_enviados = []
        for item in pecas_data:
            item['peca_empr'] = ordem.os_empr
            item['peca_fili'] = ordem.os_fili
            item['peca_os'] = ordem.os_os

            peca_item = item.get('peca_item')
            if peca_item:
                obj, _ = PecasOs.objects.using(banco).update_or_create(
                    peca_item=peca_item,
                    peca_empr=ordem.os_empr,
                    peca_fili=ordem.os_fili,
                    peca_os=ordem.os_os,
                    defaults=item
                )
                ids_enviados.append(obj.peca_item)
            else:
                obj = PecasOs.objects.using(banco).create(**item)
                ids_enviados.append(obj.peca_item)

        # Remove peças que não vieram mais
        PecasOs.objects.using(banco).filter(
            peca_os=ordem.os_os
        ).exclude(peca_item__in=ids_enviados).delete()

    def _sync_servicos(self, ordem, servicos_data, banco):
        ids_enviados = []
        for item in servicos_data:
            item['serv_empr'] = ordem.os_empr
            item['serv_fili'] = ordem.os_fili
            item['serv_os'] = ordem.os_os

            serv_item = item.get('serv_item')
            if serv_item:
                obj, _ = ServicosOs.objects.using(banco).update_or_create(
                    serv_item=serv_item,
                    serv_empr=ordem.os_empr,
                    serv_fili=ordem.os_fili,
                    serv_os=ordem.os_os,
                    defaults=item
                )
                ids_enviados.append(obj.serv_item)
            else:
                obj = ServicosOs.objects.using(banco).create(**item)
                ids_enviados.append(obj.serv_item)

        # Remove serviços que não vieram mais
        ServicosOs.objects.using(banco).filter(
            serv_os=ordem.os_os
        ).exclude(serv_item__in=ids_enviados).delete()





class OrdemServicoGeralSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdemServicoGeral
        fields = '__all__'