from rest_framework import serializers
from .models import NotaFiscal
from core.serializers import BancoContextMixin
import logging

logger = logging.getLogger(__name__)


class NotaFiscalSerializer(BancoContextMixin, serializers.ModelSerializer):
    # Campos calculados/legíveis
    numero_completo = serializers.SerializerMethodField()
    emitente_nome = serializers.CharField(source='emitente_razao_social', read_only=True)
    destinatario_nome = serializers.CharField(source='destinatario_razao_social', read_only=True)
    valor_total = serializers.DecimalField(source='valor_total_nota', max_digits=15, decimal_places=2, read_only=True)
    data_emissao_formatada = serializers.DateField(source='data_emissao', read_only=True)
    status_descricao = serializers.SerializerMethodField()
    
    class Meta:
        model = NotaFiscal
        fields = [
            # Identificação básica
            'chave_acesso',
            'numero_nota_fiscal',
            'numero_completo',
            'serie',
            'modelo',
            'data_emissao',
            'data_emissao_formatada',
            'natureza_operacao',
            
            # Emitente
            'emitente_cnpj',
            'emitente_cpf',
            'emitente_razao_social',
            'emitente_nome',
            'emitente_nome_fantasia',
            'emitente_ie',
            'emitente_logradouro',
            'emitente_numero',
            'emitente_bairro',
            'emitente_nome_municipio',
            'emitente_uf',
            'emitente_cep',
            'emitente_fone',
            
            # Destinatário
            'destinatario_cnpj',
            'destinatario_cpf',
            'destinatario_razao_social',
            'destinatario_nome',
            'destinatario_ie',
            'destinatario_logradouro',
            'destinatario_numero',
            'destinatario_bairro',
            'destinatario_nome_municipio',
            'destinatario_uf',
            'destinatario_cep',
            'destinatario_fone',
            'destinatario_email',
            
            # Valores totais
            'valor_total_produtos',
            'valor_total_nota',
            'valor_total',
            'valor_total_desconto',
            'valor_total_frete',
            'valor_total_seguro',
            'valor_total_icms',
            'valor_total_ipi',
            'valor_total_pis',
            'valor_total_cofins',
            'valor_total_outras_despesas',
            
            # Transporte
            'modalidade_frete',
            'transportador_cnpj',
            'transportador_cpf',
            'transportador_razao_social',
            'transportador_ie',
            'veiculo_placa',
            'veiculo_uf',
            
            # Status e controle
            'status_nfe',
            'status_descricao',
            'cancelada',
            'inutilizada',
            'denegada',
            'protocolo_nfe',
            
            # Configurações
            'ambiente',
            'tipo_operacao',
            'finalidade_emissao',
            'consumidor_final',
            'indicador_presenca',
            
            # Controle do sistema
            'empresa',
            'filial',
            'cliente',
            'vendedor',
            'transportadora',
            'usuario',
        ]
        
    def get_numero_completo(self, obj):
        """Retorna número completo da nota: série-número"""
        if obj.serie and obj.numero_nota_fiscal:
            return f"{obj.serie}-{obj.numero_nota_fiscal}"
        return obj.numero_nota_fiscal
        
    def get_status_descricao(self, obj):
        """Retorna descrição do status da nota fiscal"""
        if obj.cancelada:
            return "Cancelada"
        elif obj.inutilizada:
            return "Inutilizada"
        elif obj.denegada:
            return "Denegada"
        elif obj.status_nfe == 100:
            return "Autorizada"
        elif obj.status_nfe == 101:
            return "Cancelada"
        elif obj.status_nfe == 110:
            return "Denegada"
        elif obj.status_nfe == 150:
            return "Autorizada fora de prazo"
        elif obj.status_nfe == 302:
            return "Denegada por irregularidade"
        elif obj.status_nfe == 303:
            return "Denegada por irregularidade"
        else:
            return "Pendente"




class NotaFiscalListSerializer(BancoContextMixin, serializers.ModelSerializer):
    """Serializer simplificado para listagem de notas fiscais"""
    numero_completo = serializers.SerializerMethodField()
    emitente_nome = serializers.CharField(source='emitente_razao_social', read_only=True)
    destinatario_nome = serializers.CharField(source='destinatario_razao_social', read_only=True)
    valor_total = serializers.DecimalField(source='valor_total_nota', max_digits=15, decimal_places=2, read_only=True)
    status_descricao = serializers.SerializerMethodField()
    
    class Meta:
        model = NotaFiscal
        fields = [
            'chave_acesso',
            'numero_nota_fiscal',
            'numero_completo',
            'serie',
            'data_emissao',
            'natureza_operacao',
            'emitente_nome',
            'destinatario_nome',
            'valor_total',
            'status_nfe',
            'status_descricao',
            'cancelada',
            'empresa',
            'filial',
        ]
        
    def get_numero_completo(self, obj):
        """Retorna número completo da nota: série-número"""
        if obj.serie and obj.numero_nota_fiscal:
            return f"{obj.serie}-{obj.numero_nota_fiscal}"
        return obj.numero_nota_fiscal
        
    def get_status_descricao(self, obj):
        """Retorna descrição do status da nota fiscal"""
        if obj.cancelada:
            return "Cancelada"
        elif obj.inutilizada:
            return "Inutilizada"
        elif obj.denegada:
            return "Denegada"
        elif obj.status_nfe == 100:
            return "Autorizada"
        elif obj.status_nfe == 101:
            return "Cancelada"
        elif obj.status_nfe == 110:
            return "Denegada"
        elif obj.status_nfe == 150:
            return "Autorizada fora de prazo"
        elif obj.status_nfe == 302:
            return "Denegada por irregularidade"
        elif obj.status_nfe == 303:
            return "Denegada por irregularidade"
        else:
            return "Pendente"
    
    