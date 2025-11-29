from django.db import transaction
from Notas_Fiscais.services.nota_service import NotaService
from .emissao_service_core import EmissaoServiceCore
from Notas_Fiscais.dominio.builder import NotaBuilder
from Notas_Fiscais.services.calculo_impostos_service import CalculoImpostosService


class EmissaoNotaService:

    @staticmethod
    @transaction.atomic
    def emitir_nota(dto_dict, empresa, filial, usuario=None, database="default"):
        """
        Fluxo:
        1. Cria a nota (rascunho)
        2. Gera XML + envia pra SEFAZ
        3. Registra evento
        4. Atualiza status (100 ou rejeição)
        """

        # 1) Criar rascunho
        dto_sanitized = dict(dto_dict)
        dto_sanitized.pop("tpag", None)
        nota = NotaService.criar(
            data=dto_sanitized,
            itens=dto_dict.get("itens", []),
            impostos_map=None,
            transporte=None,
            empresa=empresa,
            filial=filial,
            database=database,
        )

        # buscar filial real
        from Licencas.models import Filiais
        filial_obj = Filiais.objects.using(database).filter(
            empr_empr=empresa, empr_codi=filial
        ).first()

        # 2) Aplicar impostos aos itens da nota
        CalculoImpostosService(database).aplicar_impostos(nota)

        # 3) Montar DTO a partir da Nota criada
        dto_obj = NotaBuilder(nota, database=database).build()
        dto_payload = dto_obj.dict()
        dto_payload["tpag"] = dto_dict.get("tpag")

        # 4) Emissão SEFAZ
        emissor = EmissaoServiceCore(dto_payload, filial_obj)
        resposta, xml_assinado, resposta_xml = emissor.emitir()

        cStat = resposta["status"]

        # 5) Interpretar SEFAZ
        if cStat == "100":  # OK autorizado
            NotaService.transmitir(
                nota,
                descricao="NF-e autorizada pela SEFAZ",
                chave=resposta["chave"],
                protocolo=resposta["protocolo"],
                xml=xml_assinado,
            )
        else:
            NotaService.gravar(
                nota,
                descricao=f"Rejeição SEFAZ: {resposta['status']} - {resposta['motivo']}",
            )

        return {
            "nota": nota,
            "sefaz": resposta,
            "xml_assinado": xml_assinado,
            "xml_resposta": resposta_xml,
        }
