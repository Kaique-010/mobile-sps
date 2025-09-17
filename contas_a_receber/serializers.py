from rest_framework import serializers
from Entidades.models import Entidades
from .models import Titulosreceber, Baretitulos
from decimal import Decimal
from datetime import date

class TitulosreceberSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.SerializerMethodField()
    class Meta:
        model = Titulosreceber
        fields = [
            'titu_empr','titu_fili','titu_titu','titu_seri',
            'titu_parc','titu_clie','titu_valo', 'titu_emis',
            'titu_venc','titu_situ','titu_form_reci',
            'cliente_nome', 'titu_aber'
        ]
    
    def get_cliente_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            entidades = Entidades.objects.using(banco).filter(
                enti_clie=obj.titu_clie,
                enti_empr=obj.titu_empr,
                       
            ).first()

            return entidades.enti_nome if entidades else None

        except Exception as e:
          
            return None
    
    
    def create(self, validated_data):
        banco = self.context.get('banco')
        return Titulosreceber.objects.using(banco).create(**validated_data)
    
    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)
        return instance
    
    def destroy(self, instance):
        banco = self.context.get('banco')
        instance.delete(using=banco)

class BaixaTitulosReceberSerializer(serializers.Serializer):
    data_recebimento = serializers.DateField()
    valor_recebido = serializers.DecimalField(max_digits=15, decimal_places=2)
    valor_juros = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    valor_multa = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    valor_desconto = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    historico = serializers.CharField(max_length=500, required=False, allow_blank=True)
    banco = serializers.IntegerField(required=False, allow_null=True)
    cheque = serializers.IntegerField(required=False, allow_null=True)
    tipo_baixa = serializers.CharField(max_length=1, default='T')  # T=Total, P=Parcial
    forma_pagamento = serializers.CharField(max_length=1, default='D', required=False)  # D=Dinheiro, B=Banco
    
    def validate(self, data):
        valor_recebido = data.get('valor_recebido', 0)
        valor_juros = data.get('valor_juros', 0)
        valor_multa = data.get('valor_multa', 0)
        valor_desconto = data.get('valor_desconto', 0)
        
        if valor_recebido <= 0:
            raise serializers.ValidationError("Valor recebido deve ser maior que zero")
            
        return data

class BaretitulosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Baretitulos
        fields = [
            'bare_sequ', 'bare_ctrl', 'bare_empr', 'bare_fili', 'bare_clie',
            'bare_titu', 'bare_seri', 'bare_parc', 'bare_dpag', 'bare_apag',
            'bare_vmul', 'bare_vjur', 'bare_vdes', 'bare_pago', 'bare_valo_pago',
            'bare_sub_tota', 'bare_topa', 'bare_form', 'bare_banc', 'bare_cheq', 
            'bare_hist', 'bare_emis', 'bare_venc', 'bare_usua_baix', 'bare_data_baix'
        ]

class ExcluirBaixaSerializer(serializers.Serializer):
    motivo_exclusao = serializers.CharField(max_length=500, required=False, allow_blank=True)

    
    def validate_confirmar_exclusao(self, value):
        if not value:
            raise serializers.ValidationError("É necessário confirmar a exclusão da baixa")
        return value
        
        