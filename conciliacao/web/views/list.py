from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.shortcuts import render
from django.views.decorators.http import require_GET

from conciliacao.contexto import obter_contexto
from conciliacao.models import ConciliacaoBancaria

from ..forms import ConciliacaoFiltroForm


@login_required
@require_GET
def listar(request, slug):
    ctx = obter_contexto(request, slug, acao="view")

    form = ConciliacaoFiltroForm(request.GET)
    pagina = None
    status = 200

    parametros = request.GET.copy()
    parametros.pop("page", None)

    try:
        conciliacoes = (
            ConciliacaoBancaria.objects
            .using(ctx.db_alias)
            .filter(
                empresa=ctx.empresa,
                filial=ctx.filial,
            )
            .only(
                "nume",
                "empresa",
                "filial",
                "codigo_banco",
                "data",
            )
        )

        if form.is_valid():
            filtros = {
                "numero": "nume",
                "codigo_banco": "codigo_banco",
                "data": "data",
            }

            for campo, atributo in filtros.items():
                valor = form.cleaned_data[campo]

                if valor is not None:
                    conciliacoes = conciliacoes.filter(
                        **{atributo: valor}
                    )
        else:
            conciliacoes = conciliacoes.none()

        pagina = Paginator(
            conciliacoes.order_by("-nume"),
            50,
        ).get_page(request.GET.get("page"))

    except DatabaseError:
        messages.error(
            request,
            "Não foi possível consultar as conciliações. "
            "Tente novamente mais tarde.",
        )
        status = 503

    return render(
        request,
        "conciliacao/listar.html",
        {
            "form": form,
            "contexto": ctx,
            "slug": ctx.slug,
            "page_obj": pagina,
            "querystring": parametros.urlencode(),
        },
        status=status,
    )