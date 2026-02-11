from django.db import transaction
import logging
from django.core.exceptions import ValidationError
from Entidades.models import Entidades

from Notas_Fiscais.services.nota_service import NotaService
from Notas_Fiscais.dominio.builder import NotaBuilder
from Notas_Fiscais.services.calculo_impostos_service import CalculoImpostosService

from .emissao_service_core import EmissaoServiceCore
from .validators import validar_dados_iniciais, validar_dados_calculados

logger = logging.getLogger(__name__)


class EmissaoNotaService:
    @staticmethod
    @transaction.atomic
    def emitir_nota(dto_dict, empresa, filial, usuario=None, database="default"):
        """
        Fluxo:
        1. Validação inicial dos dados
        2. Cria a nota (rascunho)
        3. Aplica impostos
        4. Validação fiscal (CSTs, totais, etc)
        5. Monta DTO a partir da Nota
        6. Gera XML + envia pra SEFAZ
        7. Atualiza status / grava evento
        """

        logger.debug("EmissaoNotaService.emitir_nota: payload de entrada: %s", dto_dict)

        validar_dados_iniciais(dto_dict)

        dto_sanitized = dict(dto_dict)
        dto_sanitized.pop("tpag", None)

        # Resolve destinatário se for dict
        dest = dto_sanitized.get("destinatario")
        if isinstance(dest, dict):
            doc = dest.get("documento")
            if not doc:
                 raise ValidationError("Documento do destinatário não informado.")
            
            # Remove caracteres não numéricos
            doc_limpo = "".join(filter(str.isdigit, str(doc)))
            
            try:
                qs = Entidades.objects.using(database).filter(enti_empr=empresa)
                if len(doc_limpo) == 14:
                    entidade = qs.get(enti_cnpj=doc_limpo)
                else:
                    entidade = qs.get(enti_cpf=doc_limpo)
                
                dto_sanitized["destinatario"] = entidade.enti_clie
            except Entidades.DoesNotExist:
                 raise ValidationError(f"Destinatário com documento {doc} não encontrado.")

        nota = NotaService.criar(
            data=dto_sanitized,
            itens=dto_dict.get("itens", []),
            impostos_map=None,
            transporte=None,
            empresa=empresa,
            filial=filial,
            database=database,
        )

        from Licencas.models import Filiais

        filial_obj = Filiais.objects.using(database).filter(
            empr_empr=empresa, empr_codi=filial
        ).first()
        if not filial_obj or not getattr(filial_obj, "empr_cert_digi", None):
            alt = Filiais.objects.using(database).filter(
                empr_empr=filial, empr_codi=empresa
            ).first()
            filial_obj = alt or filial_obj

        # 3) aplicar impostos
        CalculoImpostosService(database).aplicar_impostos(nota)

        # 3.1) Validação Fiscal pós-cálculo
        validar_dados_calculados(nota)

        # 4) montar DTO a partir da Nota
        dto_obj = NotaBuilder(nota, database=database).build()
        dto_payload = dto_obj.dict()
        dto_payload["tpag"] = dto_dict.get("tpag")

        # 5) Emissão na SEFAZ
        emissor = EmissaoServiceCore(dto_payload, filial_obj)
        resposta, xml_assinado, resposta_xml = emissor.emitir()

        cStat = resposta.get("status")
        logger.debug("XML assinado enviado:\n%s", xml_assinado)
        logger.debug("XML resposta SEFAZ:\n%s", resposta_xml)
        logger.debug("Resposta SEFAZ dict:\n%s", resposta)
        logger.debug("cStat: %s", cStat)

        if str(cStat) == "100":
            NotaService.transmitir(
                nota,
                descricao="NF-e autorizada pela SEFAZ",
                chave=resposta.get("chave"),
                protocolo=resposta.get("protocolo"),
                xml=xml_assinado,
            )
        else:
            NotaService.gravar(
                nota,
                descricao=(
                    f"Rejeição SEFAZ: {resposta.get('status')} - "
                    f"{resposta.get('motivo')}"
                ),
            )

        return {
            "nota": nota,
            "sefaz": resposta,
            "xml_assinado": xml_assinado,
            "xml_resposta": resposta_xml,
        }
