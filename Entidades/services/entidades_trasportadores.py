# servicos.py
from django.core.exceptions import ValidationError  
from ..models import Entidades
from ..utils import buscar_endereco_por_cep, proxima_entidade, gerar_cpf_fake
from .validacao_documentos import DocumentoFiscalValidacaoServico

class EntidadeTransportadoraServico:

    @staticmethod
    def cadastrar_transportadora(
        *,
        data: dict,
        empresa_id: int,
        filial_id: int,
        banco: str,
        cep_fallback: str | None = None
    ):
        cep = data["enti_cep"]
        endereco = buscar_endereco_por_cep(cep)

        if not endereco and cep_fallback:
            endereco = buscar_endereco_por_cep(cep_fallback)
            cep = cep_fallback

        if not endereco:
            raise ValidationError("CEP inválido ou não encontrado")

        proximo_clie = proxima_entidade(empresa_id, filial_id, banco)

        return Entidades.objects.using(banco).create(
            enti_nome=data["enti_nome"],
            enti_fant=data["enti_nome"],
            enti_clie=proximo_clie,
            enti_cep=cep,
            enti_cpf=(
                DocumentoFiscalValidacaoServico.validar_cpf(data.get("enti_cpf"), campo="enti_cpf")
                if data.get("enti_cpf")
                else gerar_cpf_fake()
            ),
            enti_tipo_enti="FO",
            enti_tien= 'T',
            enti_empr=empresa_id,
        )
        
