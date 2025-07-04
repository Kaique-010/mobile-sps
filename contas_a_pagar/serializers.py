from rest_framework import serializers
from Entidades.models import Entidades
from .models import Titulospagar, Bapatitulos
from decimal import Decimal
from datetime import date

class TitulospagarSerializer(serializers.ModelSerializer):
    fornecedor_nome = serializers.SerializerMethodField()
    
    class Meta:
        model = Titulospagar
        fields = [
            'titu_empr','titu_fili','titu_titu','titu_seri','titu_parc',
            'titu_forn','titu_valo','titu_emis','titu_venc','titu_situ',
            'titu_usua_lanc','titu_form_reci','fornecedor_nome', 'titu_aber'
        ]

    def get_fornecedor_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            entidades = Entidades.objects.using(banco).filter(
                enti_clie=obj.titu_forn,
                enti_empr=obj.titu_empr,                   
            ).first()

            return entidades.enti_nome if entidades else None
        except Exception as e:          
            return None
    
    def create(self, validated_data):
        banco = self.context.get('banco')
        return Titulospagar.objects.using(banco).create(**validated_data)
    
    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)
        return instance


class BaixaTitulosPagarSerializer(serializers.Serializer):
    data_pagamento = serializers.DateField()
    valor_pago = serializers.DecimalField(max_digits=15, decimal_places=2)
    valor_juros = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    valor_multa = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    valor_desconto = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    historico = serializers.CharField(max_length=500, required=False, allow_blank=True)
    banco = serializers.IntegerField(required=False, allow_null=True)
    cheque = serializers.IntegerField(required=False, allow_null=True)
    tipo_baixa = serializers.CharField(max_length=1, default='T')  # T=Total, P=Parcial
    
    def validate(self, data):
        valor_pago = data.get('valor_pago', 0)
        valor_juros = data.get('valor_juros', 0)
        valor_multa = data.get('valor_multa', 0)
        valor_desconto = data.get('valor_desconto', 0)
        
        if valor_pago <= 0:
            raise serializers.ValidationError("Valor pago deve ser maior que zero")
            
        return data

class BapatitulosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bapatitulos
        fields = '__all__'


class ExcluirBaixaSerializer(serializers.Serializer):
    motivo_exclusao = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_confirmar_exclusao(self, value):
        if not value:
            raise serializers.ValidationError("É necessário confirmar a exclusão da baixa")
        return value
    
   