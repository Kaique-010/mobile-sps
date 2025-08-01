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
    Ordemservico, Ordemservicopecas, Ordemservicoservicos,
    Ordemservicoimgantes, Ordemservicoimgdurante, Ordemservicoimgdepois
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



class OrdemServicoPecasSerializer(BancoModelSerializer):
    peca_id = serializers.IntegerField(required=False)
    peca_empr = serializers.IntegerField(required=True)
    peca_fili = serializers.IntegerField(required=True)
    peca_orde = serializers.IntegerField(required=True)
    peca_codi = serializers.CharField(required=True)
    peca_comp = serializers.CharField(required=False, allow_blank=True)
    peca_quan = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, default=0)
    peca_unit = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, default=0)
    peca_tota = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, default=0)
    produto_nome = serializers.SerializerMethodField()
   

    class Meta:
        model = Ordemservicopecas
        fields = '__all__'

    def validate(self, data):
        # Validar campos obrigatórios
        campos_obrigatorios = ['peca_empr', 'peca_fili', 'peca_orde', 'peca_codi']
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

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco de dados não fornecido.")
      
        return Ordemservicopecas.objects.using(banco).create(**validated_data)

    def get_produto_nome(self, obj):
        try:
            banco = self.context.get('banco')
            from Produtos.models import Produtos

            produto = Produtos.objects.using(banco).get(prod_codi=obj.peca_codi)
            return produto.prod_nome
        except:
            return ''
        
   



class OrdemServicoServicosSerializer(BancoModelSerializer):
    serv_id = serializers.IntegerField(required=False)
    serv_empr = serializers.IntegerField(required=True)
    serv_fili = serializers.IntegerField(required=True)
    serv_orde = serializers.IntegerField(required=True)
    serv_sequ = serializers.IntegerField(required=False)
    serv_codi = serializers.CharField(required=True)
    serv_comp = serializers.CharField(required=False, allow_blank=True)
    serv_quan = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, default=0)
    serv_unit = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, default=0)
    serv_tota = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, default=0)
    

    class Meta:
        model = Ordemservicoservicos
        fields = '__all__'
        
    
        
    def validate(self, data):
        # Validar campos obrigatórios
        campos_obrigatorios = ['serv_empr', 'serv_fili', 'serv_orde', 'serv_codi']
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
        
        return Ordemservicoservicos.objects.using(banco).create(**validated_data)



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


class OrdemServicoSerializer(BancoModelSerializer):
    pecas = OrdemServicoPecasSerializer(many=True, required=False)
    servicos = serializers.SerializerMethodField()
    cliente_nome = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Ordemservico
        fields = '__all__'

    def get_servicos(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return []
        
        servicos = Ordemservicoservicos.objects.using(banco).filter(
            serv_empr=obj.orde_empr,
            serv_fili=obj.orde_fili,
            serv_orde=obj.orde_nume
        ).order_by('serv_sequ')
        
        return OrdemServicoServicosSerializer(servicos, many=True, context=self.context).data
    
    def get_cliente_nome(self, obj):
        banco = self.context.get('banco')
        if not banco or not obj.orde_enti or not obj.orde_empr:
            return None
            
        try:
            entidade = Entidades.objects.using(banco).filter(
                enti_clie=obj.orde_enti,
                enti_empr=obj.orde_empr
            ).first()
            return entidade.enti_nome if entidade else None
        except Exception as e:
            logger.error(f"Erro ao buscar cliente: {e}")
            return None
        
            

    def validate_orde_stat(self, value):
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
            item['peca_empr'] = ordem.orde_empr
            item['peca_fili'] = ordem.orde_fili
            item['peca_orde'] = ordem.orde_nume

            peca_id = item.get('peca_id')
            if peca_id:
                obj, _ = Ordemservicopecas.objects.using(banco).update_or_create(
                    peca_id=peca_id,
                    peca_empr=ordem.orde_empr,
                    peca_fili=ordem.orde_fili,
                    peca_orde=ordem.orde_nume,
                    defaults=item
                )
                ids_enviados.append(obj.peca_id)
            else:
                obj = Ordemservicopecas.objects.using(banco).create(**item)
                ids_enviados.append(obj.peca_id)

        # Remove peças que não vieram mais
        Ordemservicopecas.objects.using(banco).filter(
            peca_orde=ordem.orde_nume
        ).exclude(peca_id__in=ids_enviados).delete()

    def _sync_servicos(self, ordem, servicos_data, banco):
        ids_enviados = []
        for item in servicos_data:
            item['serv_empr'] = ordem.orde_empr
            item['serv_fili'] = ordem.orde_fili
            item['serv_orde'] = ordem.orde_nume

            serv_id = item.get('serv_id')
            if serv_id:
                obj, _ = Ordemservicoservicos.objects.using(banco).update_or_create(
                    serv_id=serv_id,
                    serv_empr=ordem.orde_empr,
                    serv_fili=ordem.orde_fili,
                    serv_orde=ordem.orde_nume,
                    defaults=item
                )
                ids_enviados.append(obj.serv_id)
            else:
                obj = Ordemservicoservicos.objects.using(banco).create(**item)
                ids_enviados.append(obj.serv_id)

        # Remove serviços que não vieram mais
        Ordemservicoservicos.objects.using(banco).filter(
            serv_orde=ordem.orde_nume
        ).exclude(serv_id__in=ids_enviados).delete()




class ImagemBase64Serializer(BancoModelSerializer):
    imagem_base64 = serializers.SerializerMethodField()
    imagem_upload = serializers.CharField(write_only=True, required=False)

    def get_imagem_base64(self, obj):
        campo_imagem = getattr(obj, self.Meta.imagem_field, None)
        if campo_imagem and len(campo_imagem) > 0:
            try:
                return base64.b64encode(campo_imagem).decode('utf-8')
            except Exception as e:
                logger.warning(f"Erro ao codificar imagem: {e}")
        return None

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        img_base64 = data.get('imagem_upload')
        if isinstance(img_base64, str) and img_base64.strip():
            try:
                ret[self.Meta.imagem_field] = base64.b64decode(img_base64)
            except Exception as e:
                logger.warning(f"Erro ao decodificar imagem base64: {e}")
                raise ValidationError({'imagem_upload': 'Imagem inválida ou corrompida.'})
        # Remove imagem_upload from the data since it's processed and shouldn't be passed to the model
        ret.pop('imagem_upload', None)
        return ret



class OrdemServicoImgAntesSerializer(ImagemBase64Serializer):
    class Meta:
        model = Ordemservicoimgantes
        imagem_field = 'iman_imag'
        fields = [
            'iman_id', 'iman_empr', 'iman_fili', 'iman_orde', 'iman_codi',
            'iman_come', 'iman_obse', 'img_latitude', 'img_longitude',
            'img_data', 'imagem_base64', 'imagem_upload'
        ]


class ImagemAntesSerializer(ImagemBase64Serializer):
    class Meta:
        model = Ordemservicoimgantes
        imagem_field = 'iman_imag'
        fields = [
            'iman_id', 'iman_empr', 'iman_fili', 'iman_orde', 'iman_codi',
            'iman_come', 'iman_obse', 'img_latitude', 'img_longitude',
            'img_data', 'imagem_base64', 'imagem_upload'
        ]


# Imagem Durante
class ImagemDuranteSerializer(ImagemBase64Serializer):
    class Meta:
        model = Ordemservicoimgdurante
        imagem_field = 'imdu_imag'
        fields = [
            'imdu_id', 'imdu_empr', 'imdu_fili', 'imdu_orde', 'imdu_codi',
            'imdu_come', 'imdu_obse', 'img_latitude', 'img_longitude',
            'img_data', 'imagem_base64', 'imagem_upload'
        ]


# Imagem Depois
class ImagemDepoisSerializer(ImagemBase64Serializer):
    class Meta:
        model = Ordemservicoimgdepois
        imagem_field = 'imde_imag'
        fields = [
            'imde_id', 'imde_empr', 'imde_fili', 'imde_orde', 'imde_codi',
            'imde_come', 'imde_obse', 'img_latitude', 'img_longitude',
            'img_data', 'imagem_base64', 'imagem_upload'
        ]
