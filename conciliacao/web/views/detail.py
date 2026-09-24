from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from conciliacao.contexto import obter_contexto
from conciliacao.models import (
    ConciliacaoBancaria,
    ItemBanco,
    ItemExtrato,
)
from conciliacao.services.conciliar import ConciliarExtratoService


@login_required
@require_GET
def detalhe(request, slug, empresa, filial, numero):

    ctx = obter_contexto(
        request,
        slug,
        acao="view",
    )

    if empresa != ctx.empresa or filial != ctx.filial:
        raise Http404("Conciliação não encontrada.")

    dados = {
        "contexto": ctx,
        "slug": ctx.slug,
    }

    status = 200

    try:

        escopo = {
            "empresa": ctx.empresa,
            "filial": ctx.filial,
            "nume": numero,
        }

        dados["conciliacao"] = get_object_or_404(
            ConciliacaoBancaria.objects
            .using(ctx.db_alias)
            .only(
                "nume",
                "empresa",
                "filial",
                "codigo_banco",
                "data",
            ),
            **escopo
        )

        service = ConciliarExtratoService(
            banco=ctx.db_alias,
            empresa=ctx.empresa,
            filial=ctx.filial,
            numero=numero,
        )
        total_conciliados = (
            ItemExtrato.objects
            .using(ctx.db_alias)
            .filter(**escopo, selecionado=True)
            .count()
        )
 
        dados["total_conciliados"] = total_conciliados

        for modelo, nome in (
            (ItemExtrato, "extrato"),
            (ItemBanco, "banco"),
        ):

            itens = (
                modelo.objects
                .using(ctx.db_alias)
                .filter(**escopo)
                .order_by("linha", "id")
            )

            parametro = "page_{}".format(nome)

            pagina = Paginator(
                itens,
                50,
            ).get_page(
                request.GET.get(parametro)
            )

            # ==================================================
            # STATUS DA CONCILIAÇÃO
            # ==================================================

            if modelo is ItemExtrato:

                for item in pagina.object_list:

                    status_item = service._status_conciliacao(
                        item
                    )

                    item.status_conciliacao = (
                        status_item["status"]
                    )

                    item.total_vinculado = (
                        status_item["total_vinculado"]
                    )

                    item.saldo_conciliacao = (
                        status_item["saldo"]
                    )

            # ==================================================
            # PAGINAÇÃO
            # ==================================================

            parametros = request.GET.copy()
            parametros.pop(parametro, None)

            dados["pagina_{}".format(nome)] = pagina

            dados["querystring_{}".format(nome)] = (
                parametros.urlencode()
            )

    except DatabaseError:

        messages.error(
            request,
            "Não foi possível consultar a conciliação. "
            "Tente novamente mais tarde.",
        )

        dados["erro_consulta"] = True
        status = 503

    return render(
        request,
        "conciliacao/detalhe.html",
        dados,
        status=status,
    )