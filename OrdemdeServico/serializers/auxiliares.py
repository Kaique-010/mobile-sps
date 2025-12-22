from rest_framework.exceptions import ValidationError
from .base import BancoModelSerializer
from ..models import WorkflowSetor, OrdemServicoFaseSetor, OrdemServicoVoltagem

class OrdemServicoFaseSetorSerializer(BancoModelSerializer):
    class Meta:
        model = OrdemServicoFaseSetor
        fields = '__all__'
    
    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError('Banco não encontrado no contexto')
        instance = self.Meta.model.objects.using(banco).create(**validated_data)
        return instance

class OrdemServicoVoltagemSerializer(BancoModelSerializer):
    class Meta:
        model = OrdemServicoVoltagem
        fields = '__all__'
    
    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError('Banco não encontrado no contexto')
        instance = self.Meta.model.objects.using(banco).create(**validated_data)
        return instance

class WorkflowSetorSerializer(BancoModelSerializer):
    class Meta:
        model = WorkflowSetor
        fields = '__all__'
    
    def validate(self, data):
        """Validação customizada para evitar duplicatas"""
        wkfl_seto_orig = data.get('wkfl_seto_orig')
        wkfl_seto_dest = data.get('wkfl_seto_dest')
        
        if wkfl_seto_orig == wkfl_seto_dest:
            raise ValidationError("O setor de origem não pode ser igual ao setor de destino.")
        
        # Verifica se já existe a combinação
        banco = self.context.get('banco')
        if banco and wkfl_seto_orig and wkfl_seto_dest:
            exists = WorkflowSetor.objects.using(banco).filter(
                wkfl_seto_orig=wkfl_seto_orig,
                wkfl_seto_dest=wkfl_seto_dest
            ).exists()
            
            if exists:
                raise ValidationError(
                    f"Já existe um workflow do setor {wkfl_seto_orig} para o setor {wkfl_seto_dest}."
                )
        
        return data
    
    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError('Banco não encontrado no contexto')
        instance = self.Meta.model.objects.using(banco).create(**validated_data)
        return instance
