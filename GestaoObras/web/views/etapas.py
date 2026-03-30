from django.shortcuts import render, redirect, get_object_or_404
from core.utils import get_licenca_db_config
from GestaoObras.web.forms import ObraEtapaForm
from GestaoObras.models import Obra, ObraEtapa
from GestaoObras.services.obras_service import ObrasService


def listar_etapas(request, slug, obra_id: int):
    banco = get_licenca_db_config(request)
    obra = get_object_or_404(Obra.objects.using(banco), pk=obra_id)
    qs = ObraEtapa.objects.using(banco).filter(etap_obra_id=obra.id).order_by("etap_orde", "id")
    return render(request, "obras/etapas_listar.html", {"slug": slug, "obra": obra, "etapas": qs})


def criar_etapa(request, slug, obra_id: int):
    banco = get_licenca_db_config(request)
    obra = get_object_or_404(Obra.objects.using(banco), pk=obra_id)
    initial = {
        "etap_empr": obra.obra_empr,
        "etap_fili": obra.obra_fili,
        "etap_obra": obra.id,
        "etap_codi": ObrasService.proximo_codigo_etapa(banco, obra.obra_empr, obra.obra_fili),
    }
    if request.method == "POST":
        form = ObraEtapaForm(request.POST, banco=banco, initial=initial)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.etap_empr = obra.obra_empr
            obj.etap_fili = obra.obra_fili
            obj.etap_obra_id = obra.id
            obj.save(using=banco)
            return redirect("gestaoobras:obras_etapas_list", slug=slug, obra_id=obra.id)
    else:
        form = ObraEtapaForm(banco=banco, initial=initial)
    return render(request, "obras/etapas_criar.html", {"slug": slug, "obra": obra, "form": form})


def editar_etapa(request, slug, obra_id: int, etapa_id: int):
    banco = get_licenca_db_config(request)
    obra = get_object_or_404(Obra.objects.using(banco), pk=obra_id)
    etapa = get_object_or_404(ObraEtapa.objects.using(banco), pk=etapa_id, etap_obra_id=obra.id)
    initial = {"etap_empr": obra.obra_empr, "etap_fili": obra.obra_fili, "etap_obra": obra.id}

    if request.method == "POST":
        form = ObraEtapaForm(request.POST, banco=banco, initial=initial, instance=etapa)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.etap_empr = obra.obra_empr
            obj.etap_fili = obra.obra_fili
            obj.etap_obra_id = obra.id
            obj.save(using=banco)
            return redirect("gestaoobras:obras_detail", slug=slug, obra_id=obra.id)
    else:
        form = ObraEtapaForm(banco=banco, initial=initial, instance=etapa)

    return render(request, "obras/etapas_criar.html", {"slug": slug, "obra": obra, "form": form})
