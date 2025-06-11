from rest_framework import serializers
from Entidades.models import Entidades
from .models import Titulosreceber

class TitulosreceberSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.SerializerMethodField()
    class Meta:
        model = Titulosreceber
        fields = [
            'titu_empr','titu_titu','titu_seri',
            'titu_parc','titu_clie','titu_valo',
            'titu_venc','titu_situ','titu_form_reci',
            'cliente_nome'
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
        
        