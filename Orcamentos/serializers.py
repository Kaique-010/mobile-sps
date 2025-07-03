from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from Licencas.models import Empresas
from Produtos.models import Produtos
from .models import Orcamentos, ItensOrcamento
from Entidades.models import Entidades
from core.serializers import BancoContextMixin
import logging

logger = logging.getLogger(__name__)


class ItemOrcamentoSerializer(BancoContextMixin,serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField()
    class Meta:
        model = ItensOrcamento
        exclude = ['iped_empr', 'iped_fili', 'iped_item', 'iped_pedi', 'iped_data', 'iped_forn']
    
    def to_internal_value(self, data):
        # Garante que iped_desc seja sempre um valor decimal
        if 'iped_desc' in data:
            if isinstance(data['iped_desc'], bool):
                data['iped_desc'] = 0.00 if not data['iped_desc'] else 0.00
            elif data['iped_desc'] is None:
                data['iped_desc'] = 0.00
            else:
                try:
                    data['iped_desc'] = round(float(data['iped_desc']), 2)
                except (ValueError, TypeError):
                    data['iped_desc'] = 0.00
        return super().to_internal_value(data)
    
    
    def get_produto_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            logger.warning("Banco não informado no context.")
            return None
        try:
            produto = Produtos.objects.using(banco).get(prod_codi=obj.iped_prod)
            return produto.prod_nome
        except Exception as e:
            logger.error(f"Erro ao buscar produto: {e}")
            return None

            
            
class OrcamentosSerializer(BancoContextMixin, serializers.ModelSerializer):
    valor_total = serializers.FloatField(source='pedi_tota', read_only=True)
    cliente_nome = serializers.SerializerMethodField(read_only=True)
    empresa_nome = serializers.SerializerMethodField(read_only=True)
    itens = serializers.SerializerMethodField()
    itens_input = ItemOrcamentoSerializer(many=True, write_only=True, required=True)


    class Meta:
        model = Orcamentos
        fields = [
            'pedi_empr', 'pedi_fili', 'pedi_data', 'pedi_tota', 'pedi_forn', 'pedi_vend',
            'itens', 'itens_input',
            'valor_total', 'cliente_nome', 'empresa_nome', 'pedi_nume'
        ]
    
    def to_internal_value(self, data):
       
        if 'pedi_tota' in data:
            try:
                data['pedi_tota'] = round(float(data['pedi_tota']), 2)
            except (ValueError, TypeError):
                pass  # Deixa o Django validar o erro
        return super().to_internal_value(data)
    
    def get_itens(self, obj):
        banco = self.context.get('banco')
        itens = ItensOrcamento.objects.using(banco).filter(
            iped_empr=obj.pedi_empr,
            iped_fili=obj.pedi_fili,
            iped_pedi=str(obj.pedi_nume)
        )
        return ItemOrcamentoSerializer(itens, many=True, context=self.context).data


   
    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        itens_data = validated_data.pop('itens_input', [])
        if not itens_data:
            raise ValidationError("Itens do orcamento são obrigatórios.")

        orcamentos = None
        if 'pedi_nume' in validated_data:
            orcamentos = Orcamentos.objects.using(banco).filter(
                pedi_empr=validated_data['pedi_empr'],
                pedi_fili=validated_data['pedi_fili'],
                pedi_nume=validated_data['pedi_nume'],
            ).first()

        if orcamentos:
            # edição disfarçada
            ItensOrcamento.objects.using(banco).filter(
                iped_empr=orcamentos.pedi_empr,
                iped_fili=orcamentos.pedi_fili,
                iped_pedi=str(orcamentos.pedi_nume)
            ).delete()

            for attr, value in validated_data.items():
                setattr(orcamentos, attr, value)
            orcamentos.save(using=banco)
            orcamento = orcamentos
        else:
            ultimo = Orcamentos.objects.using(banco).filter(
                pedi_empr=validated_data['pedi_empr'],
                pedi_fili=validated_data['pedi_fili']
            ).order_by('-pedi_nume').first()
            validated_data['pedi_nume'] = (ultimo.pedi_nume + 1) if ultimo else 1

            orcamento = Orcamentos.objects.using(banco).create(**validated_data)

        total = 0
        for idx, item_data in enumerate(itens_data, start=1):
            # Garante que iped_desc seja um valor decimal válido
            if 'iped_desc' not in item_data or item_data['iped_desc'] is None:
                item_data['iped_desc'] = 0.00
            elif isinstance(item_data['iped_desc'], bool):
                item_data['iped_desc'] = 0.00
            
            ItensOrcamento.objects.using(banco).create(
                iped_empr=orcamento.pedi_empr,
                iped_fili=orcamento.pedi_fili,
                iped_item=idx,
                iped_pedi=str(orcamento.pedi_nume),
                iped_data=orcamento.pedi_data,
                iped_forn=orcamento.pedi_forn,
                **item_data
            )
            total += item_data.get('iped_quan', 0) * item_data.get('iped_unit', 0)

        orcamento.pedi_tota = round(total, 2)
        orcamento.save(using=banco)

        return orcamento


    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não definido no contexto.")

        itens_data = validated_data.pop('itens_input', None)
        if itens_data is None:
            raise ValidationError("Itens do orcamento são obrigatórios.")

        # Atualiza campos do orcamento
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)

        # Remove todos os itens antigos do orcamento
        ItensOrcamento.objects.using(banco).filter(
            iped_empr=instance.pedi_empr,
            iped_fili=instance.pedi_fili,
            iped_pedi=str(instance.pedi_nume)
        ).delete()

        # Recria os itens
        total = 0
        for idx, item_data in enumerate(itens_data, start=1):
            # Garante que iped_desc seja um valor decimal válido
            if 'iped_desc' not in item_data or item_data['iped_desc'] is None:
                item_data['iped_desc'] = 0.00
            elif isinstance(item_data['iped_desc'], bool):
                item_data['iped_desc'] = 0.00
            
            ItensOrcamento.objects.using(banco).create(
                iped_empr=instance.pedi_empr,
                iped_fili=instance.pedi_fili,
                iped_item=idx,
                iped_pedi=str(instance.pedi_nume),
                iped_data=instance.pedi_data,
                iped_forn=instance.pedi_forn,
                **item_data
            )
            total += item_data.get('iped_quan', 0) * item_data.get('iped_unit', 0)

        instance.pedi_tota = round(total, 2)
        instance.save(using=banco)
        return instance

 
    

    

    def get_cliente_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            entidades = Entidades.objects.using(banco).filter(
                enti_clie=obj.pedi_forn,
                enti_empr=obj.pedi_empr,
            ).first()

            return entidades.enti_nome if entidades else None

        except Exception as e:
            logger.warning(f"Erro ao buscar cliente: {e}")
            return None
        

    def get_empresa_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            return Empresas.objects.using(banco).get(empr_codi=obj.pedi_empr).empr_nome
        except Empresas.DoesNotExist:
            logger.warning(f"Empresa com ID {obj.pedi_empr} não encontrada.")
            return None

    def get_produto_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None
        try:
            produto = Produtos.objects.using(banco).filter(
                prod_codi=obj.iped_prod,
                prod_empr=obj.iped_empr
            ).first()
            return produto.prod_nome if produto else None
        except Exception as e:
            logger.warning(f"Erro ao buscar nome do produto: {e}")
            return None