from .models import NotaFiscalEntrada
from core.serializers import BancoContextMixin
import logging
from rest_framework import serializers

logger = logging.getLogger(__name__)





class NotaFiscalEntradaSerializer(BancoContextMixin, serializers.ModelSerializer):
    numero_completo = serializers.SerializerMethodField()
    emitente_nome = serializers.CharField(source='emitente_razao_social', read_only=True)
    destinatario_nome = serializers.CharField(source='destinatario_razao_social', read_only=True)
    valor_total = serializers.DecimalField(source='valor_total_nota', max_digits=15, decimal_places=2, read_only=True)
    status_descricao = serializers.SerializerMethodField()

    class Meta:
        model = NotaFiscalEntrada
        fields = [
            'numero_nota_fiscal','numero_completo','serie','modelo','data_emissao','natureza_operacao',
            'emitente_cnpj','emitente_razao_social','emitente_nome',
            'destinatario_cnpj','destinatario_razao_social','destinatario_nome',
            'valor_total_nota','valor_total',
            'status_nfe','status_descricao','cancelada',
            'empresa','filial'
        ]

    def get_numero_completo(self, obj):
        if obj.serie and obj.numero_nota_fiscal:
            return f"{obj.serie}-{obj.numero_nota_fiscal}"
        return obj.numero_nota_fiscal

    def get_status_descricao(self, obj):
        if obj.cancelada:
            return "Cancelada"
        elif obj.inutilizada:
            return "Inutilizada"
        elif obj.denegada:
            return "Denegada"
        elif obj.status_nfe == 100:
            return "Autorizada"
        else:
            return "Pendente"

class NotaFiscalEntradaListSerializer(BancoContextMixin, serializers.ModelSerializer):
    numero_completo = serializers.SerializerMethodField()
    emitente_nome = serializers.CharField(source='emitente_razao_social', read_only=True)
    valor_total = serializers.DecimalField(source='valor_total_nota', max_digits=15, decimal_places=2, read_only=True)
    status_descricao = serializers.SerializerMethodField()

    class Meta:
        model = NotaFiscalEntrada
        fields = [
            'numero_nota_fiscal','numero_completo','serie','data_emissao',
            'emitente_nome','valor_total','status_nfe','status_descricao','empresa','filial'
        ]

    def get_numero_completo(self, obj):
        if obj.serie and obj.numero_nota_fiscal:
            return f"{obj.serie}-{obj.numero_nota_fiscal}"
        return obj.numero_nota_fiscal

    def get_status_descricao(self, obj):
        if obj.cancelada:
            return "Cancelada"
        elif obj.inutilizada:
            return "Inutilizada"
        elif obj.denegada:
            return "Denegada"
        elif obj.status_nfe == 100:
            return "Autorizada"
        else:
            return "Pendente"


class ImportarNotasDestinadasSerializer(serializers.Serializer):
    """
    Payload para disparar a importação de Notas Destinadas.
    """
    uf = serializers.CharField(max_length=2, required=False, allow_blank=True)
    cnpj = serializers.CharField(max_length=14, required=False, allow_blank=True)
    ultimo_nsu = serializers.CharField(max_length=20, default='0', required=False, allow_blank=True)
    caminho_pfx = serializers.CharField(required=False, allow_blank=True)
    senha_pfx = serializers.CharField(required=False, allow_blank=True)
    ambiente = serializers.IntegerField(default=1, required=False)
    empresa = serializers.IntegerField(required=False)
    filial = serializers.IntegerField(required=False)
    cliente = serializers.IntegerField(required=False, allow_null=True)
    gerar_estoque = serializers.BooleanField(default=True)
    gerar_contas_pagar = serializers.BooleanField(default=True)
    manifestar_ciencia = serializers.BooleanField(default=True)
