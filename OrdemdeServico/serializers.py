import base64
import logging
from datetime import datetime, date
from django.db.models import Max
from django.db import transaction, IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from Entidades.models import Entidades
from contas_a_receber.models import Titulosreceber
from core.serializers import BancoContextMixin
from .models import (
    Ordemservico, Ordemservicopecas, Ordemservicoservicos,
    Ordemservicoimgantes, Ordemservicoimgdurante, Ordemservicoimgdepois, 
    WorkflowSetor, OrdemServicoFaseSetor, OrdensEletro, OrdemServicoVoltagem
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


class OrdemServicoPecasSerializer(serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField()
    peca_id = serializers.IntegerField(required=False)  # Será gerado automaticamente
    peca_empr = serializers.IntegerField(required=True)
    peca_fili = serializers.IntegerField(required=True)
    peca_orde = serializers.IntegerField(required=True)
    peca_codi = serializers.CharField(required=True)
    peca_comp = serializers.CharField(required=False, allow_blank=True)
    peca_quan = serializers.DecimalField(max_digits=15, decimal_places=4, required=True)
    peca_unit = serializers.DecimalField(max_digits=15, decimal_places=4, required=True)
    peca_tota = serializers.DecimalField(max_digits=15, decimal_places=4, required=False)
   

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
        

        # Calcular o total se não fornecido
        if 'peca_tota' not in data and 'peca_quan' in data and 'peca_unit' in data:
            data['peca_tota'] = data['peca_quan'] * data['peca_unit']

        return data

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco de dados não fornecido.")
      
        return Ordemservicopecas.objects.using(banco).create(**validated_data)

    def update(self, instance, validated_data):
        for key in ['peca_id', 'peca_empr', 'peca_fili', 'peca_orde']:
            if key in validated_data:
                validated_data.pop(key)

        quan = validated_data.get('peca_quan')
        unit = validated_data.get('peca_unit')
        if quan is not None and unit is not None and 'peca_tota' not in validated_data:
            try:
                validated_data['peca_tota'] = quan * unit
            except Exception:
                pass

        return super().update(instance, validated_data)

    def get_produto_nome(self, obj):
        try:
            banco = self.context.get('banco')
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
        except Exception:
            return ""


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
    servico_nome = serializers.SerializerMethodField()
    

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
        

        # Calcular o total se não fornecido
        if 'serv_tota' not in data and 'serv_quan' in data and 'serv_unit' in data:
            data['serv_tota'] = data['serv_quan'] * data['serv_unit']

        return data

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco de dados não fornecido.")
        
        return Ordemservicoservicos.objects.using(banco).create(**validated_data)

    def update(self, instance, validated_data):
        # Protege campos de chave para evitar alteração acidental do PK/identificação
        for key in ['serv_id', 'serv_empr', 'serv_fili', 'serv_orde', 'serv_sequ']:
            if key in validated_data:
                validated_data.pop(key)

        # Recalcula total quando quantidade/unidade fornecidos e total ausente
        quan = validated_data.get('serv_quan')
        unit = validated_data.get('serv_unit')
        if quan is not None and unit is not None and 'serv_tota' not in validated_data:
            try:
                validated_data['serv_tota'] = quan * unit
            except Exception:
                pass

        return super().update(instance, validated_data)

    def get_servico_nome(self, obj):
        try:
            banco = self.context.get('banco')
            from Produtos.models import Produtos
            produto = Produtos.objects.using(banco).filter(
                prod_codi=obj.serv_codi
            ).first()
            return produto.prod_nome if produto else ''
        except Exception:
            return ''


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


class ImagemBase64Serializer(BancoModelSerializer):
    imagem_base64 = serializers.SerializerMethodField()
    imagem_data_uri = serializers.SerializerMethodField()
    imagem_upload = serializers.CharField(write_only=True, required=False)

    def validate_img_data(self, value):
        """Valida data da imagem para evitar anos inválidos"""
        if value and isinstance(value, datetime):
            if value.year < 1900 or value.year > 2100:
                raise ValidationError('Ano da data da imagem deve estar entre 1900 e 2100.')
        return value

    def get_imagem_base64(self, obj):
        campo_imagem = getattr(obj, self.Meta.imagem_field, None)
        if campo_imagem and len(campo_imagem) > 0:
            try:
                return base64.b64encode(campo_imagem).decode('utf-8')
            except Exception as e:
                logger.warning(f"Erro ao codificar imagem: {e}")
        return None

    def get_imagem_data_uri(self, obj):
        campo_imagem = getattr(obj, self.Meta.imagem_field, None)
        if campo_imagem and len(campo_imagem) > 0:
            try:
                b64 = base64.b64encode(campo_imagem).decode('utf-8')
                mime = self._detectar_mime(campo_imagem)
                return f"data:{mime};base64,{b64}"
            except Exception:
                return None
        return None

    def _detectar_mime(self, blob):
        try:
            head = bytes(blob)[:12]
        except Exception:
            return 'image/octet-stream'
        if len(head) >= 3 and head[0] == 0xFF and head[1] == 0xD8 and head[2] == 0xFF:
            return 'image/jpeg'
        if len(head) >= 8 and head[:8] == b"\x89PNG\r\n\x1a\n":
            return 'image/png'
        if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            return 'image/webp'
        return 'image/octet-stream'

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        img_base64 = data.get('imagem_upload')
        if isinstance(img_base64, str) and img_base64.strip():
            try:
                texto = img_base64.strip()
                if ',' in texto:
                    texto = texto.split(',', 1)[1]
                ret[self.Meta.imagem_field] = base64.b64decode(texto)
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
            'img_data', 'imagem_base64', 'imagem_data_uri', 'imagem_upload'
        ]


class ImagemAntesSerializer(ImagemBase64Serializer):
    class Meta:
        model = Ordemservicoimgantes
        imagem_field = 'iman_imag'
        fields = [
            'iman_id', 'iman_empr', 'iman_fili', 'iman_orde', 'iman_codi',
            'iman_come', 'iman_obse', 'img_latitude', 'img_longitude',
            'img_data', 'imagem_base64', 'imagem_data_uri', 'imagem_upload'
        ]


class ImagemDuranteSerializer(ImagemBase64Serializer):
    class Meta:
        model = Ordemservicoimgdurante
        imagem_field = 'imdu_imag'
        fields = [
            'imdu_id', 'imdu_empr', 'imdu_fili', 'imdu_orde', 'imdu_codi',
            'imdu_come', 'imdu_obse', 'img_latitude', 'img_longitude',
            'img_data', 'imagem_base64', 'imagem_data_uri', 'imagem_upload'
        ]


class ImagemDepoisSerializer(ImagemBase64Serializer):
    class Meta:
        model = Ordemservicoimgdepois
        imagem_field = 'imde_imag'
        fields = [
            'imde_id', 'imde_empr', 'imde_fili', 'imde_orde', 'imde_codi',
            'imde_come', 'imde_obse', 'img_latitude', 'img_longitude',
            'img_data', 'imagem_base64', 'imagem_data_uri', 'imagem_upload'
        ]


class OrdensEletroSerializer(serializers.ModelSerializer):
    # Campos com nomes compatíveis com o frontend
    total_os = serializers.DecimalField(source='total_orde', max_digits=12, decimal_places=2, read_only=True)
    status_ordem = serializers.CharField(source='status_orde', max_length=50, read_only=True)
    
    class Meta:
        model = OrdensEletro
        fields = [
            'empresa', 'filial', 'ordem_de_servico', 'cliente', 'nome_cliente',
            'data_abertura', 'data_fim', 'setor', 'setor_nome', 'pecas', 'servicos',
            'total_orde', 'total_os', 'status_orde', 'status_ordem', 'responsavel', 
            'nome_responsavel', 'potencia', 'ultima_alteracao'
        ]


class OrdemServicoSerializer(BancoModelSerializer):
    pecas = OrdemServicoPecasSerializer(many=True, required=False)
    servicos = OrdemServicoServicosSerializer(many=True, required=False)
    setor_nome = serializers.SerializerMethodField(read_only=True)
    cliente_nome = serializers.SerializerMethodField(read_only=True)
    proximos_setores = serializers.SerializerMethodField(read_only=True)
    pode_avancar = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Ordemservico
        fields = '__all__'
    
    def validate(self, data):
        """Validação específica por tipo de ordem"""
        data = super().validate(data)
        
        orde_tipo = data.get('orde_tipo')
        if not orde_tipo:
            return data
            
        # Configuração de campos obrigatórios por tipo
        campos_obrigatorios_por_tipo = {
            "1": ['orde_pote', 'orde_volt', 'orde_ampe', 'orde_hz', 'orde_rpm', 'orde_marc'],  # Motor C.A
            "2": ['orde_pote', 'orde_volt', 'orde_ampe', 'orde_rpm', 'orde_marc'],  # Motor C.C
            "3": ['orde_pote', 'orde_volt', 'orde_ampe', 'orde_hz', 'orde_rpm', 'orde_marc'],  # Motor E.X
            "4": ['orde_pote', 'orde_volt', 'orde_ampe', 'orde_marc'],  # Motor Síncrono
            "5": ['orde_pote', 'orde_volt', 'orde_ampe', 'orde_hz', 'orde_rpm', 'orde_marc'],  # Motor Monofásico
            "6": ['orde_pote', 'orde_volt', 'orde_ampe', 'orde_hz', 'orde_marc'],  # Transformador
            "7": ['orde_pote', 'orde_volt', 'orde_ampe', 'orde_rpm', 'orde_marc'],  # Servo Motor
            "8": ['orde_pote', 'orde_volt', 'orde_ampe', 'orde_hz', 'orde_marc'],  # Drives
            "9": ['orde_pote', 'orde_volt', 'orde_ampe', 'orde_hz', 'orde_rpm', 'orde_marc'],  # Campo M.C.A
            "10": ['orde_pote', 'orde_volt', 'orde_ampe', 'orde_hz', 'orde_marc'],  # Campo Transformador
            "11": ['orde_pote', 'orde_volt', 'orde_ampe', 'orde_hz', 'orde_rpm', 'orde_marc'],  # Campo Geral
            "12": ['orde_pote', 'orde_volt', 'orde_ampe', 'orde_hz', 'orde_rpm', 'orde_marc'],  # Motor Bomba
            "13": ['orde_pote', 'orde_rpm', 'orde_marc'],  # Bomba
            "14": ['orde_pote', 'orde_rpm', 'orde_marc'],  # Redutor
            "15": ['orde_pote', 'orde_volt', 'orde_ampe', 'orde_hz', 'orde_rpm', 'orde_marc'],  # Gerador
            "16": [],  
            "17": ['orde_pote', 'orde_volt', 'orde_ampe', 'orde_hz', 'orde_rpm', 'orde_marc'],  # Carcaça
        }
        
        campos_obrigatorios = campos_obrigatorios_por_tipo.get(orde_tipo, [])
        
        for campo in campos_obrigatorios:
            valor = data.get(campo)
            if not valor or (isinstance(valor, str) and valor.strip() == ''):
                from .models import OrdensTipos
                tipo_nome = dict(OrdensTipos).get(orde_tipo, f"Tipo {orde_tipo}")
                raise ValidationError(f"Campo '{campo}' é obrigatório para o tipo de ordem '{tipo_nome}'")
        
        # Validar datas
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
        """Valida data de abertura para evitar anos inválidos"""
        if value and isinstance(value, date):
            if value.year < 1900 or value.year > 2100:
                raise ValidationError('Ano da data de abertura deve estar entre 1900 e 2100.')
        return value

    def validate_orde_data_fech(self, value):
        """Valida data de fechamento para evitar anos inválidos"""
        if value and isinstance(value, date):
            if value.year < 1900 or value.year > 2100:
                raise ValidationError('Ano da data de fechamento deve estar entre 1900 e 2100.')
        return value

    def validate_orde_ulti_alte(self, value):
        """Valida data de última alteração para evitar anos inválidos"""
        if value and isinstance(value, datetime):
            if value.year < 1900 or value.year > 2100:
                raise ValidationError('Ano da data de última alteração deve estar entre 1900 e 2100.')
        return value

    def validate_orde_nume(self, value):
        """Valida se o número da ordem já existe"""
        banco = self.context.get('banco')
        if not banco:
            # Se não tem banco no contexto, talvez seja um update ou não conseguimos validar agora.
            return value
        
        # No create, verificamos se existe. No update, ignoramos se for o mesmo objeto.
        if self.instance:
            return value
            
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
        """Retorna próximos setores disponíveis no workflow com múltiplas opções"""
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
        """Verifica se o usuário atual pode avançar esta ordem"""
        request = self.context.get('request')
        if not request or not request.user:
            return False
        
        setor_user = getattr(request.user, "usua_seto", None) or getattr(request.user, "setor", None)
        
        # Admin pode mover qualquer ordem
        if setor_user is None:
            return True
        
        # Converte para int se necessário
        try:
            setor_user = int(setor_user)
        except (ValueError, TypeError):
            return False
            
        # Para outros usuários, só pode mover se estiver no setor atual da ordem
        return obj.orde_seto == setor_user

    # NOTE: create and update are removed here because they should be handled by the Service layer
    # or the standard BancoModelSerializer if no side effects are needed.
    # The ViewSet should orchestrate the creation/update and call the Service for syncing items.
