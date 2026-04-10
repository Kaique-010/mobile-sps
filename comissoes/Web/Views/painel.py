from django.shortcuts import render


def painel_view(request, slug=None):
    return render(request, "comissoes/base.html", {"slug": slug})
