from django.db import transaction
from django.core.exceptions import ValidationError

from core.utils import get_db_from_slug

from contas_a_pagar.models import Titulospagar
from contas_a_pagar.services import baixar_titulo_pagar

from contas_a_receber.models import Titulosreceber
from contas_a_receber.services import baixar_titulo_receber


class BaixasEmMassaService:
    """
    Regras:
    - ou baixa tudo ou nada
    - se qualquer título falhar, rollback geral
    - reaproveita os services unitários de pagar/receber
    - lançamento bancário já é gerado pelos services unitários
    """

    def executar(
        self,
        *,
        slug: str,
        ids_pagar=None,
        ids_receber=None,
        data_baixa=None,
        banco_id=None,
        centro_custo=None,
        forma_pagamento='B',
        usuario_id=None,
        valor_juros=0,
        valor_multa=0,
        valor_desconto=0,
        historico=None,
        cheque=None,
    ):
        db_alias = get_db_from_slug(slug)
        if not db_alias:
            raise ValidationError({"detail": ["Banco de dados da licença não encontrado."]})

        ids_pagar = ids_pagar or []
        ids_receber = ids_receber or []

        if not ids_pagar and not ids_receber:
            raise ValidationError({"detail": ["Nenhum título informado para baixa em massa."]})

        if not data_baixa:
            raise ValidationError({"data_baixa": ["Informe a data da baixa."]})

        if not banco_id:
            raise ValidationError({
                "banco": [
                    "Informe o banco/caixa para a baixa em massa. "
                    "Sem isso o lançamento bancário não fica previsível."
                ]
            })

        avisos = []
        if not centro_custo:
            avisos.append(
                "Centro de custo não informado. Será usado o centro de custo do título, Se existir."
            )

        resultado = {
            "sucesso": False,
            "mensagem": "",
            "avisos": avisos,
            "processados": {
                "pagar": 0,
                "receber": 0,
            },
            "baixas": {
                "pagar": [],
                "receber": [],
            },
        }

        with transaction.atomic(using=db_alias):
            if ids_pagar:
                self._processar_pagar(
                    db_alias=db_alias,
                    ids=ids_pagar,
                    data_baixa=data_baixa,
                    banco_id=banco_id,
                    centro_custo=centro_custo,
                    forma_pagamento=forma_pagamento,
                    valor_juros=valor_juros,
                    valor_multa=valor_multa,
                    valor_desconto=valor_desconto,
                    historico=historico,
                    cheque=cheque,
                    resultado=resultado,
                )

            if ids_receber:
                self._processar_receber(
                    db_alias=db_alias,
                    ids=ids_receber,
                    data_baixa=data_baixa,
                    banco_id=banco_id,
                    centro_custo=centro_custo,
                    forma_pagamento=forma_pagamento,
                    valor_juros=valor_juros,
                    valor_multa=valor_multa,
                    valor_desconto=valor_desconto,
                    historico=historico,
                    cheque=cheque,
                    usuario_id=usuario_id,
                    resultado=resultado,
                )

        resultado["sucesso"] = True
        resultado["mensagem"] = (
            f"Baixa em massa concluída com sucesso. "
            f"{resultado['processados']['pagar']} título(s) a pagar e "
            f"{resultado['processados']['receber']} título(s) a receber processados."
        )
        return resultado

    def _processar_pagar(
        self,
        *,
        db_alias,
        ids,
        data_baixa,
        banco_id,
        centro_custo,
        forma_pagamento,
        valor_juros,
        valor_multa,
        valor_desconto,
        historico,
        cheque,
        resultado,
    ):
        titulos = list(
            Titulospagar.objects.using(db_alias).filter(
                pk__in=ids,
                titu_aber__in=['A', 'P'],
            )
        )

        encontrados = {obj.pk for obj in titulos}
        faltantes = [pk for pk in ids if pk not in encontrados]
        if faltantes:
            raise ValidationError({
                "detail": [
                    f"Existem títulos a pagar não encontrados ou não disponíveis para baixa: {faltantes}"
                ]
            })

        for titulo in titulos:
            try:
                dados = {
                    "data_pagamento": data_baixa,
                    "banco": banco_id,
                    "centro_custo": centro_custo,
                    "forma_pagamento": forma_pagamento,
                    "valor_pago": titulo.titu_valo,
                    "valor_juros": valor_juros,
                    "valor_multa": valor_multa,
                    "valor_desconto": valor_desconto,
                    "historico": historico or f"Baixa em massa do título {titulo.titu_titu}",
                    "cheque": cheque,
                }

                baixa, lancamento = baixar_titulo_pagar(
                    titulo,
                    banco=db_alias,
                    dados=dados,
                )

                resultado["baixas"]["pagar"].append({
                    "titulo": titulo.titu_titu,
                    "serie": titulo.titu_seri,
                    "parcela": titulo.titu_parc,
                    "fornecedor": titulo.titu_forn,
                    "baixa_sequencia": baixa.bapa_sequ,
                    "lancamento_bancario": getattr(lancamento, "laba_ctrl", None),
                })
                resultado["processados"]["pagar"] += 1

            except Exception as exc:
                raise ValidationError({
                    "detail": [
                        (
                            f"Falha ao baixar título a pagar "
                            f"{titulo.titu_titu}/{titulo.titu_seri}-{titulo.titu_parc} "
                            f"do fornecedor {titulo.titu_forn}: {str(exc)}"
                        )
                    ]
                })

    def _processar_receber(
        self,
        *,
        db_alias,
        ids,
        data_baixa,
        banco_id,
        centro_custo,
        forma_pagamento,
        valor_juros,
        valor_multa,
        valor_desconto,
        historico,
        cheque,
        usuario_id,
        resultado,
    ):
        titulos = list(
            Titulosreceber.objects.using(db_alias).filter(
                pk__in=ids,
                titu_aber__in=['A', 'P'],
            )
        )

        encontrados = {obj.pk for obj in titulos}
        faltantes = [pk for pk in ids if pk not in encontrados]
        if faltantes:
            raise ValidationError({
                "detail": [
                    f"Existem títulos a receber não encontrados ou não disponíveis para baixa: {faltantes}"
                ]
            })

        for titulo in titulos:
            try:
                dados = {
                    "data_recebimento": data_baixa,
                    "banco": banco_id,
                    "centro_custo": centro_custo,
                    "forma_pagamento": forma_pagamento,
                    "valor_recebido": titulo.titu_valo,
                    "valor_juros": valor_juros,
                    "valor_multa": valor_multa,
                    "valor_desconto": valor_desconto,
                    "historico": historico or f"Baixa em massa do título {titulo.titu_titu}",
                    "cheque": cheque,
                }

                baixa, lancamento = baixar_titulo_receber(
                    titulo,
                    banco=db_alias,
                    dados=dados,
                    usuario_id=usuario_id,
                )

                resultado["baixas"]["receber"].append({
                    "titulo": titulo.titu_titu,
                    "serie": titulo.titu_seri,
                    "parcela": titulo.titu_parc,
                    "cliente": titulo.titu_clie,
                    "baixa_sequencia": baixa.bare_sequ,
                    "lancamento_bancario": getattr(lancamento, "laba_ctrl", None),
                })
                resultado["processados"]["receber"] += 1

            except Exception as exc:
                raise ValidationError({
                    "detail": [
                        (
                            f"Falha ao baixar título a receber "
                            f"{titulo.titu_titu}/{titulo.titu_seri}-{titulo.titu_parc} "
                            f"do cliente {titulo.titu_clie}: {str(exc)}"
                        )
                    ]
                })