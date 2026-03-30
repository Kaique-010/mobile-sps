from django.shortcuts import render, redirect
from core.utils import get_licenca_db_config
from GestaoObras.web.forms import ObraForm
from GestaoObras.models import Obra
from GestaoObras.services.obras_service import ObrasService

def criar_obra(request, slug):
    banco = get_licenca_db_config(request)
    empresa = request.GET.get("empr") or request.headers.get("X-Empresa") or request.session.get("empresa_id")
    filial = request.GET.get("fili") or request.headers.get("X-Filial") or request.session.get("filial_id")
    if request.method == "POST":
        form = ObraForm(request.POST, banco=banco)
        if form.is_valid():
            obj = form.save(commit=False)
            if empresa:
                obj.obra_empr = int(empresa)
            if filial:
                obj.obra_fili = int(filial)
            if not obj.obra_codi and empresa and filial:
                obj.obra_codi = ObrasService.proximo_codigo_obra(banco, int(empresa), int(filial))
            obj.save(using=banco)
            return redirect("gestaoobras:obras_list", slug=slug)
    else:
        initial = {}
        if empresa:
            initial["obra_empr"] = empresa
        if filial:
            initial["obra_fili"] = filial
        if empresa and filial:
            initial["obra_codi"] = ObrasService.proximo_codigo_obra(banco, int(empresa), int(filial))
        form = ObraForm(banco=banco, initial=initial)
    return render(request, "obras/criar.html", {"slug": slug, "form": form})
