# servicos.py
from django.core.exceptions import ValidationError  
from ..models import Entidades
from ..utils import buscar_endereco_por_cep, proxima_entidade
from .validacao_documentos import DocumentoFiscalValidacaoServico


class EntidadeCadastroRapido:

    @staticmethod
    def cadastrar_rapido(*, data, empresa_id, filial_id, banco, cep_fallback=None, cpf=None):
        cep = data.get("enti_cep", "").replace("-", "").strip()
        cpf = data.get("enti_cpf", "").strip()

        if not cpf:
            raise ValidationError("CPF inválido ou não fornecido")

        try:
            cpf = DocumentoFiscalValidacaoServico.validar_cpf(cpf, campo="enti_cpf")
        except Exception:
            raise ValidationError("CPF inválido ou não fornecido")

        # Tenta usar os campos já preenchidos pelo frontend (hidden fields)
        uf    = data.get("enti_esta", "").strip()
        cida  = data.get("enti_cida", "").strip()
        ende  = data.get("enti_ende", "").strip()
        bair  = data.get("enti_bair", "").strip()
        ibge  = data.get("enti_codi_cida", "").strip()

        # Se não veio do frontend, busca via API
        if not uf or not cida:
            endereco = buscar_endereco_por_cep(cep)

            if not endereco and cep_fallback:
                endereco = buscar_endereco_por_cep(cep_fallback)
                cep = cep_fallback

            if not endereco:
                raise ValidationError("CEP inválido ou não encontrado")

            uf   = endereco.get("uf", "")
            cida = endereco.get("localidade", "")
            ende = endereco.get("logradouro", "")
            bair = endereco.get("bairro", "")
            ibge = endereco.get("ibge", "")

        proximo_clie = proxima_entidade(empresa_id, filial_id, banco)

        return Entidades.objects.using(banco).create(
            enti_nome=data["enti_nome"],
            enti_fant=data["enti_nome"],
            enti_clie=proximo_clie,
            enti_cep=cep,
            enti_cpf=cpf,
            enti_tipo_enti="AM",
            enti_empr=empresa_id,
            enti_ende=ende,
            enti_bair=bair,
            enti_cida=cida,
            enti_esta=uf,
            enti_codi_cida=ibge,
        )
