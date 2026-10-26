from rest_framework.response import Response
from rest_framework import serializers
from rest_framework import status
from django.db.models import Max
from django.db import connections
from .models import Entidades
from Licencas.models  import Empresas
from .services.validacao_documentos import DocumentoFiscalValidacaoServico

_ENTIDADES_COLUMNS_CACHE = {}


def _get_entidades_table_columns(banco):
    if not banco:
        return set()
    if banco in _ENTIDADES_COLUMNS_CACHE:
        return _ENTIDADES_COLUMNS_CACHE[banco]
    try:
        connection = connections[banco]
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(cursor, Entidades._meta.db_table)
        cols = {getattr(col, "name", col[0]) for col in description}
    except Exception:
        cols = set()
    _ENTIDADES_COLUMNS_CACHE[banco] = cols
    return cols


class EntidadesSerializer(serializers.ModelSerializer):
    
    empresa_nome = serializers.SerializerMethodField()
    enti_tien = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    enti_espe_enti = serializers.ChoiceField(
        choices=Entidades.CLASSIFICACAO_TRIBUTACAO,
        required=False,
        allow_null=True,
        default='000',
    )
    enti_espe_enti_label = serializers.SerializerMethodField()

    class Meta:
        model = Entidades
        read_only_fields = ['enti_clie']
        exclude = ['enti_dana']

    def get_fields(self):
        fields = super().get_fields()
        banco = self.context.get("banco")
        cols = _get_entidades_table_columns(banco)
        if not cols:
            return fields
        for f in Entidades._meta.concrete_fields:
            if f.column not in cols and f.name in fields:
                fields.pop(f.name, None)
        return fields

    def validate(self, data):
        
        banco  = self.context.get ('banco')
        
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        
        erros = {}
        if not data.get("enti_espe_enti"):
            data["enti_espe_enti"] = "000"
        obrigatorios = ['enti_nome', 'enti_cep', 'enti_ende', 'enti_nume', 'enti_cida', 'enti_esta']

        for campo in obrigatorios:
            if not data.get(campo):
                erros[campo] = ['Este Campo é Obrigatório.']

        
        if 'enti_clie' in data:
            if Entidades.objects.using(banco).filter(enti_clie=data['enti_clie']).exists():
                erros['enti_clie'] = ['Este código já existe.']

        cpf = data.get("enti_cpf")
        cnpj = data.get("enti_cnpj")
        ie = data.get("enti_insc_esta")

        if cpf and (cnpj or ie):
            erros["enti_cpf"] = ["Se o CPF for fornecido, CNPJ e Inscrição Estadual não devem ser preenchidos."]

        if cpf:
            try:
                data["enti_cpf"] = DocumentoFiscalValidacaoServico.validar_cpf(cpf, campo="enti_cpf")
            except Exception as e:
                msg = getattr(e, "message_dict", {}).get("enti_cpf") or "CPF inválido."
                erros["enti_cpf"] = [msg]

        if cnpj:
            try:
                data["enti_cnpj"] = DocumentoFiscalValidacaoServico.validar_cnpj(cnpj, campo="enti_cnpj")
            except Exception as e:
                msg = getattr(e, "message_dict", {}).get("enti_cnpj") or "CNPJ inválido."
                erros["enti_cnpj"] = [msg]

        if erros:
            raise serializers.ValidationError(erros)

        return data

    def create(self, validated_data):
        banco = self.context.get('banco')
        
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        
        
        if not validated_data.get('enti_clie'):
            max_enti = Entidades.objects.using(banco).aggregate(Max('enti_clie'))['enti_clie__max'] or 0
            validated_data['enti_clie'] = max_enti + 1
        validated_data.setdefault('enti_espe_enti', '000')
        return Entidades.objects.using(banco).create(**validated_data)
    
    
    
    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        validated_data.pop('enti_clie', None)
        validated_data.pop('enti_empr', None)
        if 'enti_espe_enti' not in validated_data and not getattr(instance, 'enti_espe_enti', None):
            validated_data['enti_espe_enti'] = '000'
        Entidades.objects.using(banco).filter(
            enti_empr=instance.enti_empr,
            enti_clie=instance.enti_clie,
        ).update(**validated_data)
        instance = Entidades.objects.using(banco).filter(
            enti_empr=instance.enti_empr,
            enti_clie=instance.enti_clie,
        ).first() or instance
        return instance

    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['enti_fant'].required = False
        if 'enti_espe_enti' in self.fields:
            self.fields['enti_espe_enti'].required = False
        # Marca o campo do arquiteto não obrigatório se existir
        if 'enti_arqu' in self.fields:
            self.fields['enti_arqu'].required = False

    
    def get_empresa_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None
        try:
            if obj and obj.enti_empr is not None:
                empresa = Empresas.objects.using(banco).filter(empr_codi=obj.enti_empr).first()
                return empresa.empr_nome if empresa else None
        except Exception as e:
            return None
        return None

    def get_enti_espe_enti_label(self, obj):
        try:
            return obj.get_enti_espe_enti_display()
        except Exception:
            return None



    def to_representation(self, instance):
        try:
            ret = super().to_representation(instance)
            
            campos_inteiros = ['enti_clie', 'enti_empr']
            for field in campos_inteiros:
                if ret.get(field) == '':
                    ret[field] = None

            return ret
        except Exception as e:
            campos_inteiros = ['enti_clie', 'enti_empr']
            for field in campos_inteiros:
                try:
                    valor = getattr(instance, field, None)
                    self.fields[field].to_representation(valor)
                except Exception as inner_e:
                    print(f"\n❌ Erro no campo: {field}")
                    print(f"👉 Valor: {valor!r}")
                    print(f"💥 Erro: {inner_e}")
                    break
            raise e  # Relevanta o erro original depois de logar


class EntidadesTipoOutrosSerializer(serializers.Serializer):
    enti_nome = serializers.CharField(max_length=255)
    enti_cep = serializers.CharField(max_length=8, required=False, allow_blank=True)


class EntidadesCadastroRapidoCreateSerializer(serializers.Serializer):
    enti_cpf = serializers.CharField(max_length=11, required=False, allow_blank=True)
    enti_cep = serializers.CharField(max_length=8, required=False, allow_blank=True)
    enti_nome = serializers.CharField(max_length=255)

    def validate_enti_cpf(self, value):
        if not value:
            return value
        try:
            return DocumentoFiscalValidacaoServico.validar_cpf(value, campo="enti_cpf")
        except Exception:
            raise serializers.ValidationError("CPF inválido.")
