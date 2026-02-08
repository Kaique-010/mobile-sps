from rest_framework import serializers
from ..models import Tabelaprecos
from core.serializers import BancoContextMixin
from decimal import Decimal, ROUND_HALF_UP
import logging

logger = logging.getLogger(__name__)

class TabelaPrecoSerializer(BancoContextMixin, serializers.ModelSerializer):
    percentual_avis = serializers.FloatField(write_only=True, required=False)
    percentual_apra = serializers.FloatField(write_only=True, required=False)
    

    class Meta:
        model = Tabelaprecos
        fields = [
            'tabe_empr', 'tabe_fili', 'tabe_prod',
            'tabe_prco', 'tabe_cuge', 'tabe_avis', 'tabe_apra',
            'tabe_desc', 'tabe_marg', 'tabe_vare',
            'tabe_cust', 'tabe_icms', 'tabe_valo_st',
            'percentual_avis', 'percentual_apra',
            'field_log_data', 'field_log_time', 'tabe_hist', 'tabe_entr'
        ]
        extra_kwargs = {
            'tabe_empr': {'read_only': True},
            'tabe_fili': {'read_only': True},
            'tabe_prod': {'read_only': True},
            'field_log_data': {'read_only': True},
            'field_log_time': {'read_only': True},
        }

    def to_internal_value(self, data):
        # Converter strings vazias para None antes da validação
        decimal_fields = [
            'tabe_prco', 'tabe_icms', 'tabe_desc', 'tabe_vipi', 'tabe_pipi',
            'tabe_fret', 'tabe_desp', 'tabe_cust', 'tabe_marg', 'tabe_impo',
            'tabe_avis', 'tabe_praz', 'tabe_apra', 'tabe_vare', 'tabe_valo_st',
            'tabe_perc_reaj', 'tabe_cuge', 'tabe_perc_st'
        ]
        
        for field in decimal_fields:
            if field in data and (data[field] == '' or data[field] is None):
                data[field] = None
                
        return super().to_internal_value(data)

    def validate(self, data):
        campos_preco = ['tabe_prco', 'tabe_avis', 'tabe_apra', 'tabe_cuge', 'tabe_vare']
        for campo in campos_preco:
            valor = data.get(campo)
            if valor is not None and Decimal(valor) < 0:
                raise serializers.ValidationError({campo: "O preço não pode ser negativo"})

        if 'tabe_prco' in data:
            preco_base = Decimal(data['tabe_prco'])
            if 'percentual_avis' in data:
                percentual = Decimal(str(data.pop('percentual_avis')))
                data['tabe_avis'] = (preco_base * (Decimal('1') + percentual / 100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if 'percentual_apra' in data:
                percentual = Decimal(str(data.pop('percentual_apra')))
                data['tabe_apra'] = (preco_base * (Decimal('1') + percentual / 100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return data

    def create(self, validated_data):
        using = self.context.get('using') or self.context.get('banco')
        if not using:
            raise serializers.ValidationError("Banco de dados não especificado")

        # garante que as chaves existem, pegando do contexto se não vier no validated_data
        tabe_empr = validated_data.get('tabe_empr') or self.context.get('tabe_empr')
        tabe_fili = validated_data.get('tabe_fili') or self.context.get('tabe_fili')
        tabe_prod = validated_data.get('tabe_prod') or self.context.get('tabe_prod')

        if not all([tabe_empr, tabe_fili, tabe_prod]):
            raise serializers.ValidationError("Campos tabe_empr, tabe_fili e tabe_prod são obrigatórios")

        try:
            instance = Tabelaprecos.objects.using(using).get(
                tabe_empr=tabe_empr,
                tabe_fili=tabe_fili,
                tabe_prod=tabe_prod
            )
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save(using=using)
            return instance
        except Tabelaprecos.DoesNotExist:
            # adiciona os campos obrigatórios no validated_data antes de criar
            validated_data['tabe_empr'] = tabe_empr
            validated_data['tabe_fili'] = tabe_fili
            validated_data['tabe_prod'] = tabe_prod
            return Tabelaprecos.objects.using(using).create(**validated_data)


    def update(self, instance, validated_data):
        using = self.context.get('using') or self.context.get('banco')
        if not using:
            raise serializers.ValidationError("Banco de dados não especificado")

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=using, force_update=True)
        return instance

    
    def to_representation(self, instance):
        """Validar dados antes da serialização"""
        # Verificar se tabe_entr tem data válida
        if hasattr(instance, 'tabe_entr') and instance.tabe_entr:
            try:
                year = instance.tabe_entr.year
                if year < 1900 or year > 2100:
                    logger.warning(f"Data inválida em tabe_entr: {instance.tabe_entr} - Produto: {instance.tabe_prod}")
                    instance.tabe_entr = None
            except (ValueError, AttributeError) as e:
                logger.warning(f"Erro na data tabe_entr: {e} - Produto: {instance.tabe_prod}")
                instance.tabe_entr = None
        
        return super().to_representation(instance)
