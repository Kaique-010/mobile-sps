from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from conciliacao.contexto import obter_contexto
from conciliacao.models import ConciliacaoBancaria, ItemBanco, ItemExtrato


@login_required
@require_GET
def detalhe(request, slug, empresa, filial, numero):
    ctx = obter_contexto(request, slug, acao="view")
    if empresa != ctx.empresa or filial != ctx.filial:
        raise Http404("Conciliação não encontrada.")
    dados = {"contexto": ctx, "slug": ctx.slug}
    status = 200
    try:
        escopo = {"empresa": ctx.empresa, "filial": ctx.filial, "nume": numero}
        dados["conciliacao"] = get_object_or_404(
            ConciliacaoBancaria.objects.using(ctx.db_alias).only(
                "nume", "empresa", "filial", "codigo_banco", "data"
            ), **escopo
        )
        for modelo, nome in ((ItemExtrato, "extrato"), (ItemBanco, "banco")):
            itens = modelo.objects.using(ctx.db_alias).filter(**escopo).order_by("linha", "id")
            parametro = "page_{}".format(nome)
            pagina = Paginator(itens, 50).get_page(request.GET.get(parametro))
            pagina.object_list = list(pagina.object_list)
            parametros = request.GET.copy()
            parametros.pop(parametro, None)
            dados["pagina_{}".format(nome)] = pagina
            dados["querystring_{}".format(nome)] = parametros.urlencode()
    except DatabaseError:
        messages.error(request, "Não foi possível consultar a conciliação. Tente novamente mais tarde.")
        dados["erro_consulta"] = True
        status = 503
    return render(request, "conciliacao/detalhe.html", dados, status=status)
