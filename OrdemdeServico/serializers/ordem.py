import logging
from datetime import datetime, date
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from Entidades.models import Entidades
from ..models import Ordemservico, Ordemservicoservicos, OrdemServicoFaseSetor
from .base import BancoModelSerializer
from .itens import OrdemServicoPecasSerializer, OrdemServicoServicosSerializer

logger = logging.getLogger(__name__)

class OrdemServicoSerializer(BancoModelSerializer):
    pecas = OrdemServicoPecasSerializer(many=True, required=False)
    servicos = serializers.SerializerMethodField()
    setor_nome = serializers.SerializerMethodField(read_only=True)
    cliente_nome = serializers.SerializerMethodField(read_only=True)
    proximos_setores = serializers.SerializerMethodField(read_only=True)
    pode_avancar = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Ordemservico
        fields = '__all__'
    
    def validate(self, data):
        data = super().validate(data)
        
        orde_tipo = data.get('orde_tipo')
        if not orde_tipo:
            return data
            
        # Validação geral
        data_aber = data.get('orde_data_aber')
        data_fech = data.get('orde_data_fech')
        if data_aber and data_fech:
           if data_fech < data_aber:
                raise ValidationError('Data de fechamento não pode ser anterior à data de abertura.')

        return data
    
    def validate_orde_stat(self, value):
        VALID_STATUSES = [0, 1, 2, 3, 4, 5, 20, 21]
        if value not in VALID_STATUSES:
            raise ValidationError('Status inválido.')
        return value

    def validate_orde_data_aber(self, value):
        if value and isinstance(value, date):
            if value.year < 1900 or value.year > 2100:
                raise ValidationError('Ano da data de abertura deve estar entre 1900 e 2100.')
        return value

    def validate_orde_data_fech(self, value):
        if value and isinstance(value, date):
            if value.year < 1900 or value.year > 2100:
                raise ValidationError('Ano da data de fechamento deve estar entre 1900 e 2100.')
        return value

    def validate_orde_ulti_alte(self, value):
        if value and isinstance(value, datetime):
            if value.year < 1900 or value.year > 2100:
                raise ValidationError('Ano da data de última alteração deve estar entre 1900 e 2100.')
        return value

    def validate_orde_nume(self, value):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError('Banco não informado.')
        if Ordemservico.objects.using(banco).filter(orde_nume=value).exists():
            raise ValidationError('Número de ordem já existe.')
        return value

    def get_produto_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return ""
        try:
            from django.db.models import Q
            from Produtos.models import Produtos
            codigo = str(obj.peca_codi)
            empresa = str(getattr(obj, 'peca_empr', ''))
            qs = Produtos.objects.using(banco).filter(
                Q(prod_codi=codigo) | Q(prod_codi_nume=codigo)
            )
            if empresa:
                qs = qs.filter(prod_empr=empresa)
            produto = qs.first()
            return produto.prod_nome if produto else ""
        except Exception as e:
            logger.error(f"Erro ao buscar nome do produto {obj.peca_codi}: {str(e)}")
            return ""

    def get_servicos(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return []
        try:
            servicos = Ordemservicoservicos.objects.using(banco).filter(
                serv_empr=obj.orde_empr,
                serv_fili=obj.orde_fili,
                serv_orde=obj.orde_nume
            )
            return OrdemServicoServicosSerializer(servicos, many=True, context=self.context).data
        except Exception as e:
            logger.error(f"Erro ao buscar serviços da ordem {obj.orde_nume}: {str(e)}")
            return []
    
    def get_cliente_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None
        try:
            entidade = Entidades.objects.using(banco).filter(
                enti_empr=obj.orde_empr,
                enti_clie=obj.orde_enti
            ).first()
            return entidade.enti_nome if entidade else None
        except Exception as e:
            logger.error(f"Erro ao buscar cliente da ordem {obj.orde_nume}: {str(e)}")
            return None
    
    def get_setor_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None
        try:
            setor = OrdemServicoFaseSetor.objects.using(banco).filter(
                osfs_codi=obj.orde_seto
             ).first()
            return setor.osfs_nome if setor else None
        except Exception as e:
            logger.error(f"Erro ao buscar setor da ordem {obj.orde_nume}: {str(e)}")
            return None

    def get_proximos_setores(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return []
        try:
            setores = obj.obter_proximos_setores(banco)
            return [
                {
                    "codigo": setor.wkfl_seto_dest, 
                    "nome": f"Setor {setor.wkfl_seto_dest}",
                    "ordem": setor.wkfl_orde
                }
                for setor in setores
            ]
        except Exception as e:
            logger.error(f"Erro ao buscar próximos setores da ordem {obj.orde_nume}: {str(e)}")
            return []

    def get_pode_avancar(self, obj):
        request = self.context.get('request')
        if not request or not request.user:
            return False
        
        setor_user = getattr(request.user, "usua_seto", None) or getattr(request.user, "setor", None)
        if setor_user is None:
            return True
        
        try:
            setor_user = int(setor_user)
        except (ValueError, TypeError):
            return False
            
        return obj.orde_seto == setor_user

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
        from ..models import Ordemservicopecas
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

        Ordemservicopecas.objects.using(banco).filter(
            peca_orde=ordem.orde_nume
        ).exclude(peca_id__in=ids_enviados).delete()

    def _sync_servicos(self, ordem, servicos_data, banco):
        from ..models import Ordemservicoservicos
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

        Ordemservicoservicos.objects.using(banco).filter(
            serv_orde=ordem.orde_nume
        ).exclude(serv_id__in=ids_enviados).delete()
