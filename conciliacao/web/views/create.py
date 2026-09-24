from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from conciliacao.contexto import obter_contexto
from conciliacao.services.importador_ofx import ImportarOFXService

from ..forms import ImportarOFXForm


@login_required
@require_http_methods(["GET", "POST"])
def importar(request, slug):
    ctx = obter_contexto(request, slug, acao="add")

    form = ImportarOFXForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        contexto=ctx,
    )

    status = 200

    if request.method == "POST" and form.is_valid():
        try:
            resultado = ImportarOFXService(
                empresa=ctx.empresa,
                filial=ctx.filial,
                codigo_banco=int(form.cleaned_data["codigo_banco"]),
                db_alias=ctx.db_alias,
            ).importar_upload(form.cleaned_data["arquivo"])

            messages.success(
                request,
                "Conciliação {} importada: {} transações.".format(
                    resultado["numero_conciliacao"],
                    resultado["total_importado"],
                ),
            )

            return redirect(
                "conciliacao:detalhe",
                slug=ctx.slug,
                empresa=ctx.empresa,
                filial=ctx.filial,
                numero=resultado["numero_conciliacao"],
            )

        except ValidationError as erro:
            for mensagem in erro.messages:
                form.add_error(None, mensagem)

        except DatabaseError:
            form.add_error(
                None,
                "Não foi possível acessar os dados da conciliação. "
                "Tente novamente mais tarde.",
            )
            status = 503

    return render(
        request,
        "conciliacao/importar.html",
        {
            "form": form,
            "contexto": ctx,
            "slug": ctx.slug,
        },
        status=status,
    )