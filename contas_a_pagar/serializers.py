from rest_framework import serializers
from Entidades.models import Entidades
from .models import Titulospagar

class TitulospagarSerializer(serializers.ModelSerializer):
    fornecedor_nome = serializers.SerializerMethodField()
    
    class Meta:
        model = Titulospagar
        fields = [
            'titu_empr',
            'titu_titu',
            'titu_seri',
            'titu_parc',
            'titu_forn',
            'titu_valo',
            'titu_venc',
            'titu_situ',
            'titu_usua_lanc',
            'titu_form_reci', 
            'fornecedor_nome'
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