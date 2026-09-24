import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from conciliacao.contexto import obter_contexto
from conciliacao.services.conciliar import ConciliarExtratoService


logger = logging.getLogger(__name__)


@login_required
@require_POST
def desvincular(
    request,
    slug,
    empresa,
    filial,
    numero,
):
    """
    Desvincula um lançamento da conciliação.

    O ID do vínculo é recebido através do POST:

        hist_id
    """

    # =========================================================
    # OBTÉM O CONTEXTO
    # =========================================================

    ctx = obter_contexto(
        request,
        slug,
        acao="view",
    )


    # =========================================================
    # VALIDA EMPRESA E FILIAL
    # =========================================================

    if (
        empresa != ctx.empresa
        or filial != ctx.filial
    ):

        return JsonResponse(
            {
                "sucesso": False,
                "erro": "Você não tem acesso a esta conciliação."
            },
            status=403,
        )


    # =========================================================
    # PEGA O ID DO VÍNCULO
    # =========================================================

    hist_id = request.POST.get("hist_id")


    # =========================================================
    # VALIDA O ID
    # =========================================================

    if not hist_id:

        return JsonResponse(
            {
                "sucesso": False,
                "erro": "ID do vínculo não informado."
            },
            status=400,
        )


    # =========================================================
    # CONVERTE O ID PARA INTEIRO
    # =========================================================

    try:

        hist_id = int(hist_id)

    except (TypeError, ValueError):

        return JsonResponse(
            {
                "sucesso": False,
                "erro": "ID do vínculo inválido."
            },
            status=400,
        )


    # =========================================================
    # CRIA O SERVICE
    # =========================================================

    service = ConciliarExtratoService(
        banco=ctx.db_alias,
        empresa=ctx.empresa,
        filial=ctx.filial,
        numero=numero,
    )


    # =========================================================
    # EXECUTA O DESVINCULAMENTO
    # =========================================================

    try:

        service.desvincular(
            hist_id=hist_id
        )


    # =========================================================
    # ERRO DE VALIDAÇÃO
    # =========================================================

    except ValidationError as exc:

        logger.warning(
            "Validação ao desvincular conciliação: "
            "slug=%s empresa=%s filial=%s numero=%s hist_id=%s erro=%s",
            slug,
            empresa,
            filial,
            numero,
            hist_id,
            exc,
        )

        return JsonResponse(
            {
                "sucesso": False,
                "erro": str(exc),
            },
            status=400,
        )


    # =========================================================
    # ERRO DE BANCO
    # =========================================================

    except DatabaseError:

        logger.exception(
            "Erro ao desvincular conciliação: "
            "slug=%s empresa=%s filial=%s numero=%s hist_id=%s",
            slug,
            empresa,
            filial,
            numero,
            hist_id,
        )

        return JsonResponse(
            {
                "sucesso": False,
                "erro": (
                    "Erro ao desvincular. "
                    "Consulte o log do servidor."
                ),
            },
            status=500,
        )


    # =========================================================
    # SUCESSO
    # =========================================================

    return JsonResponse(
        {
            "sucesso": True,
            "hist_id": hist_id,
            "mensagem": "Vínculo desfeito com sucesso.",
        }
    )