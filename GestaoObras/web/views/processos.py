from django.shortcuts import render, redirect, get_object_or_404
from core.utils import get_licenca_db_config
from GestaoObras.web.forms import ObraProcessoForm
from GestaoObras.models import Obra, ObraEtapa, ObraProcesso


def listar_processos(request, slug, obra_id: int):
    banco = get_licenca_db_config(request)
    obra = get_object_or_404(Obra.objects.using(banco), pk=obra_id)
    qs = ObraProcesso.objects.using(banco).filter(proc_obra_id=obra.id).order_by("-proc_codi")
    etapa_id = request.GET.get("etapa_id")
    status = request.GET.get("status")
    if etapa_id:
        qs = qs.filter(proc_etap_id=etapa_id)
    if status:
        qs = qs.filter(proc_stat=status)
    etapas = ObraEtapa.objects.using(banco).filter(etap_obra_id=obra.id).order_by("etap_orde", "id")
    return render(
        request,
        "obras/processos_listar.html",
        {"slug": slug, "obra": obra, "processos": qs, "etapas": etapas, "etapa_id": etapa_id, "status": status},
    )


def criar_processo(request, slug, obra_id: int):
    banco = get_licenca_db_config(request)
    obra = get_object_or_404(Obra.objects.using(banco), pk=obra_id)
    initial = {"proc_empr": obra.obra_empr, "proc_fili": obra.obra_fili, "proc_obra": obra.id}
    if request.method == "POST":
        form = ObraProcessoForm(request.POST, banco=banco, initial=initial)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.proc_empr = obra.obra_empr
            obj.proc_fili = obra.obra_fili
            obj.proc_obra_id = obra.id
            if obj.proc_etap_id:
                exists = ObraEtapa.objects.using(banco).filter(pk=obj.proc_etap_id, etap_obra_id=obra.id).exists()
                if not exists:
                    obj.proc_etap_id = None
            obj.save(using=banco)
            return redirect("gestaoobras:obras_processos_list", slug=slug, obra_id=obra.id)
    else:
        form = ObraProcessoForm(banco=banco, initial=initial)
    return render(request, "obras/processos_criar.html", {"slug": slug, "obra": obra, "form": form})


def editar_processo(request, slug, obra_id: int, processo_id: int):
    banco = get_licenca_db_config(request)
    obra = get_object_or_404(Obra.objects.using(banco), pk=obra_id)
    proc = get_object_or_404(ObraProcesso.objects.using(banco), pk=processo_id, proc_obra_id=obra.id)
    initial = {"proc_empr": obra.obra_empr, "proc_fili": obra.obra_fili, "proc_obra": obra.id}

    if request.method == "POST":
        form = ObraProcessoForm(request.POST, banco=banco, initial=initial, instance=proc)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.proc_empr = obra.obra_empr
            obj.proc_fili = obra.obra_fili
            obj.proc_obra_id = obra.id
            if obj.proc_etap_id:
                exists = ObraEtapa.objects.using(banco).filter(pk=obj.proc_etap_id, etap_obra_id=obra.id).exists()
                if not exists:
                    obj.proc_etap_id = None
            obj.save(using=banco)
            return redirect("gestaoobras:obras_detail", slug=slug, obra_id=obra.id)
    else:
        form = ObraProcessoForm(banco=banco, initial=initial, instance=proc)

    return render(request, "obras/processos_criar.html", {"slug": slug, "obra": obra, "form": form})
