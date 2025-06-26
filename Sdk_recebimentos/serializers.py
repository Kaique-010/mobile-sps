
from rest_framework import serializers
from .models import RecebimentoSdk, TituloReceberSdk
from core.middleware import get_licenca_slug

class RecebimentoSdkSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecebimentoSdk
        fields = '__all__'
    
    def validate(self, data):
        """
        Validação customizada para verificar se já existe um recebimento
        com a mesma combinação de empresa, filial e pedido.
        """
        slug = get_licenca_slug()
        if slug:
            existing = RecebimentoSdk.objects.using(slug).filter(
                sdk_empr=data.get('sdk_empr'),
                sdk_fili=data.get('sdk_fili'),
                sdk_pedi=data.get('sdk_pedi')
            ).exists()
            
            if existing:
                raise serializers.ValidationError(
                    "Já existe um recebimento registrado para esta combinação de empresa, filial e pedido."
                )
        
        # Validação para parcelas
        if data.get('sdk_tipo') in ['pix', 'debito'] and data.get('sdk_parc', 1) > 1:
            raise serializers.ValidationError(
                "Pagamentos PIX e débito não podem ter parcelas."
            )
        
        if data.get('sdk_tipo') == 'credito' and data.get('sdk_parc', 1) < 1:
            raise serializers.ValidationError(
                "Pagamentos a crédito devem ter pelo menos 1 parcela."
            )
        
        return data



class TituloReceberSdkSerializer(serializers.ModelSerializer):
    class Meta:
        model = TituloReceberSdk
        fields = '__all__'
