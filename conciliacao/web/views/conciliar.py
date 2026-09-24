from datetime import date
from decimal import Decimal, InvalidOperation
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from ...contexto import obter_contexto
from conciliacao.services.conciliar import ConciliarExtratoService


logger = logging.getLogger(__name__)


def _redirect_detalhe(slug, empresa, filial, numero):
    return redirect(
        "conciliacao:detalhe",
        slug=slug,
        empresa=empresa,
        filial=filial,
        numero=numero,
    )


def _parse_decimal(valor, mensagem="Valor inválido."):
    try:
        valor = Decimal(str(valor).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError, AttributeError):
        raise ValidationError(mensagem)

    if not valor.is_finite() or valor <= 0:
        raise ValidationError("O valor deve ser maior que zero.")

    return valor


def _obter_titulos_post(request, origem):
    """
    Converte os campos repetidos do formulário
    em uma lista de títulos para o serviço.
    """

    if origem == "RECEBER":
        entidades = request.POST.getlist("cliente[]")
        campo_entidade = "cliente"

    elif origem == "PAGAR":
        entidades = request.POST.getlist("fornecedor[]")
        campo_entidade = "fornecedor"

    else:
        raise ValidationError("Origem inválida.")

    titulos = request.POST.getlist("titulo[]")
    series = request.POST.getlist("serie[]")
    parcelas = request.POST.getlist("parcela[]")
    valores = request.POST.getlist("valor[]")

    tamanhos = {
        len(entidades),
        len(titulos),
        len(series),
        len(parcelas),
        len(valores),
    }

    if len(tamanhos) != 1:
        raise ValidationError(
            "Os dados dos títulos enviados estão incompletos."
        )

    resultado = []

    for entidade, titulo, serie, parcela, valor in zip(
        entidades,
        titulos,
        series,
        parcelas,
        valores,
    ):
        if not all([
            entidade,
            titulo,
            serie,
            parcela,
            valor,
        ]):
            raise ValidationError(
                "Preencha todos os campos dos títulos."
            )

        valor_decimal = _parse_decimal(
            valor,
            "Foi informado um valor inválido.",
        )

        resultado.append({
            campo_entidade: entidade,
            "titulo": titulo.strip(),
            "serie": serie.strip(),
            "parcela": parcela.strip(),
            "valor": valor_decimal,
        })

    if not resultado:
        raise ValidationError(
            "Informe ao menos um título para conciliar."
        )

    return resultado


@login_required
@require_POST
def conciliar(request, slug, empresa, filial, numero):
    """
    Processa a conciliação de um item do extrato.

    Origem:
        RECEBER -> baixa títulos a receber
        PAGAR   -> baixa títulos a pagar
        AVULSO  -> cria lançamento bancário sem título
    """

    ctx = obter_contexto(
        request,
        slug,
        acao="view",
    )

    if empresa != ctx.empresa or filial != ctx.filial:
        messages.error(
            request,
            "Você não tem acesso a esta conciliação.",
        )

        return _redirect_detalhe(
            slug,
            empresa,
            filial,
            numero,
        )

    item_extrato_id = request.POST.get("item_extrato_id")
    origem = request.POST.get("origem", "").strip().upper()

    if not item_extrato_id:
        messages.error(
            request,
            "Nenhum item do extrato foi informado.",
        )

        return _redirect_detalhe(
            slug,
            empresa,
            filial,
            numero,
        )

    try:
        item_extrato_id = int(item_extrato_id)

        if item_extrato_id <= 0:
            raise ValueError

    except (TypeError, ValueError):
        messages.error(
            request,
            "Item do extrato inválido.",
        )

        return _redirect_detalhe(
            slug,
            empresa,
            filial,
            numero,
        )

    if origem not in ("RECEBER", "PAGAR", "AVULSO"):
        messages.error(
            request,
            "Origem de conciliação inválida.",
        )

        return _redirect_detalhe(
            slug,
            empresa,
            filial,
            numero,
        )

    service = ConciliarExtratoService(
        banco=ctx.db_alias,
        empresa=ctx.empresa,
        filial=ctx.filial,
        numero=numero,
    )

    try:

        # ======================================================
        # LANÇAMENTO AVULSO
        # ======================================================

        if origem == "AVULSO":

            valor_avulso = request.POST.get("valor_avulso")
            data_lancamento = request.POST.get("data_baixa")
            historico = request.POST.get(
                "historico_avulso",
                "",
            ).strip()
            banco = request.POST.get("banco")

            if not valor_avulso:
                raise ValidationError(
                    "Informe o valor do lançamento avulso."
                )

            if not data_lancamento:
                raise ValidationError(
                    "Informe a data do lançamento."
                )

            if not historico:
                raise ValidationError(
                    "Informe o histórico do lançamento."
                )

            if not banco:
                raise ValidationError(
                    "Informe o banco/conta do lançamento."
                )

            valor_avulso = _parse_decimal(
                valor_avulso,
                "O valor do lançamento avulso é inválido.",
            )

            try:
                data_lancamento = date.fromisoformat(
                    data_lancamento
                )
            except (TypeError, ValueError):
                raise ValidationError(
                    "Data do lançamento inválida."
                )

            try:
                banco = int(banco)
            except (TypeError, ValueError):
                raise ValidationError(
                    "Banco/conta inválido."
                )

            resultado = service.lancar_avulso(
                item_extrato_id=item_extrato_id,
                valor=valor_avulso,
                data_lancamento=data_lancamento,
                historico=historico,
                banco=banco,
            )

            messages.success(
                request,
                "Lançamento avulso realizado com sucesso. "
                f"Controle bancário: {resultado.laba_ctrl}.",
            )

            return _redirect_detalhe(
                slug,
                empresa,
                filial,
                numero,
            )

        # ======================================================
        # RECEBER / PAGAR
        # ======================================================

        data_baixa = request.POST.get("data_baixa")
        forma = request.POST.get("forma")

        if not data_baixa or not forma:
            messages.error(
                request,
                "Informe a data e a forma de pagamento.",
            )

            return _redirect_detalhe(
                slug,
                empresa,
                filial,
                numero,
            )

        try:
            data_baixa = date.fromisoformat(data_baixa)
        except (TypeError, ValueError):
            raise ValidationError(
                "Data da baixa inválida."
            )

        titulos_selecionados = _obter_titulos_post(
            request,
            origem,
        )

        if origem == "RECEBER":

            resultado = service.conciliar_recebimentos(
                item_extrato_id=item_extrato_id,
                titulos=titulos_selecionados,
                data_recebimento=data_baixa,
                forma_recebimento=forma,
            )

        else:

            resultado = service.conciliar_pagamentos(
                item_extrato_id=item_extrato_id,
                titulos=titulos_selecionados,
                data_pagamento=data_baixa,
                forma_pagamento=forma,
            )

        messages.success(
            request,
            "Conciliação realizada com sucesso. "
            f"Total vinculado: R$ "
            f"{resultado['total_vinculado']:.2f}.",
        )

    except (ValidationError, ValueError) as exc:

        messages.error(
            request,
            str(exc),
        )

    except DatabaseError:

        logger.exception(
            "Erro de banco ao conciliar extrato. "
            "slug=%s empresa=%s filial=%s numero=%s "
            "item_extrato_id=%s origem=%s db_alias=%s",
            slug,
            empresa,
            filial,
            numero,
            item_extrato_id,
            origem,
            ctx.db_alias,
        )

        messages.error(
            request,
            "Erro ao acessar o banco de dados. "
            "Consulte o log do servidor para identificar a causa.",
        )

    except Exception:
        # Captura qualquer erro inesperado (ex: NameError, AttributeError
        # de código do service) para não estourar 500 silencioso e
        # sempre voltar pro usuário com feedback + log completo.
        logger.exception(
            "Erro inesperado ao conciliar extrato. "
            "slug=%s empresa=%s filial=%s numero=%s "
            "item_extrato_id=%s origem=%s",
            slug,
            empresa,
            filial,
            numero,
            item_extrato_id,
            origem,
        )

        messages.error(
            request,
            "Erro inesperado ao processar a conciliação. "
            "Consulte o log do servidor para identificar a causa.",
        )

    return _redirect_detalhe(
        slug,
        empresa,
        filial,
        numero,
    )