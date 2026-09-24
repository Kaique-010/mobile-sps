from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ...contexto import obter_contexto

from contas_a_receber.models import Titulosreceber
from contas_a_pagar.models import Titulospagar


@login_required
@require_GET
def buscar_titulos_abertos(request, slug, empresa, filial, numero):
    """
    Retorna os títulos em aberto (titu_aber = 'A') de um
    cliente ou fornecedor, para preencher o modal de conciliação.

    Query params:
    - origem: RECEBER ou PAGAR
    - entidade: código do cliente/fornecedor
    """

    ctx = obter_contexto(request, slug, acao="view")

    if empresa != ctx.empresa or filial != ctx.filial:
        return JsonResponse(
            {"erro": "Você não tem acesso a esta conciliação."},
            status=403,
        )

    origem = request.GET.get("origem", "").strip().upper()
    entidade_raw = request.GET.get("entidade", "").strip()

    if origem not in ("RECEBER", "PAGAR"):
        return JsonResponse(
            {"erro": "Origem inválida."},
            status=400,
        )

    if not entidade_raw:
        return JsonResponse(
            {"erro": "Informe o cliente/fornecedor."},
            status=400,
        )

    try:
        entidade = int(entidade_raw)
    except ValueError:
        return JsonResponse(
            {"erro": "Cliente/fornecedor inválido."},
            status=400,
        )

    if origem == "RECEBER":
        qs = (
            Titulosreceber.objects
            .using(ctx.db_alias)
            .filter(
                titu_empr=empresa,
                titu_fili=filial,
                titu_clie=entidade,
                titu_aber="A",
            )
            .order_by("titu_venc")
            .values(
                "titu_titu",
                "titu_seri",
                "titu_parc",
                "titu_valo",
                "titu_venc",
            )[:50]
        )
    else:
        qs = (
            Titulospagar.objects
            .using(ctx.db_alias)
            .filter(
                titu_empr=empresa,
                titu_fili=filial,
                titu_forn=entidade,
                titu_aber="A",
            )
            .order_by("titu_venc")
            .values(
                "titu_titu",
                "titu_seri",
                "titu_parc",
                "titu_valo",
                "titu_venc",
            )[:50]
        )

    titulos = [
        {
            "titulo": item["titu_titu"],
            "serie": item["titu_seri"],
            "parcela": item["titu_parc"],
            "valor": str(item["titu_valo"] or "0.00"),
            "vencimento": (
                item["titu_venc"].isoformat()
                if item["titu_venc"]
                else None
            ),
        }
        for item in qs
    ]

    return JsonResponse({"titulos": titulos})