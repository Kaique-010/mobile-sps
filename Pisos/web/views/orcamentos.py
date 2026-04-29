from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from core.utils import get_db_from_slug
from Pisos.models import Orcamentopisos
from Pisos.services.web_flow_service import exportar_orcamento_para_pedido, OrcamentoPisosWebFlowService


def listar_orcamentos_pisos(request, slug):
    banco = get_db_from_slug(slug)
    orcamentos = Orcamentopisos.objects.using(banco).order_by('-orca_nume')[:200]
    return render(request, 'Pisos/orcamentos_listar.html', {'slug': slug, 'orcamentos': orcamentos})


def exportar_orcamento_pedido(request, slug, numero):
    banco = get_db_from_slug(slug)
    orc = get_object_or_404(Orcamentopisos.objects.using(banco), orca_nume=numero)
    try:
        pedido_numero = exportar_orcamento_para_pedido(banco, orc.orca_empr, orc.orca_fili, orc.orca_nume)
        messages.success(request, f'Orçamento {numero} exportado para pedido {pedido_numero}.')
    except Exception as exc:
        messages.error(request, f'Erro ao exportar: {exc}')
    return redirect('PisosWeb:orcamentos_pisos_listar', slug=slug)


def criar_orcamento_pisos(request, slug):
    banco = get_db_from_slug(slug)
    empresa_id = request.session.get("empresa_id")
    filial_id = request.session.get("filial_id")

    if request.method == "POST":
        if not empresa_id or not filial_id:
            messages.error(request, "Sessão inválida: empresa/filial não informadas.")
            return redirect("PisosWeb:orcamentos_pisos_listar", slug=slug)

        payload = {
            "orca_empr": empresa_id,
            "orca_fili": filial_id,
            "orca_clie": request.POST.get("orca_clie") or None,
            "orca_vend": request.POST.get("orca_vend") or None,
            "orca_data": request.POST.get("orca_data") or timezone.localdate(),
            "orca_data_prev_entr": request.POST.get("orca_data_prev_entr") or None,
            "orca_obse": request.POST.get("orca_obse") or "",
            "orca_desc": request.POST.get("orca_desc") or 0,
            "orca_fret": request.POST.get("orca_fret") or 0,
            "itens_input": [{
                "item_ambi": 1,
                "item_nome_ambi": request.POST.get("item_nome_ambi") or "Padrão",
                "item_prod": request.POST.get("item_prod"),
                "item_prod_nome": request.POST.get("item_prod_nome") or "",
                "item_m2": request.POST.get("item_m2") or 0,
                "item_quan": request.POST.get("item_quan") or 0,
                "item_unit": request.POST.get("item_unit") or 0,
                "item_queb": request.POST.get("item_queb") or 0,
                "item_desc": request.POST.get("item_desc") or 0,
                "item_obse": request.POST.get("item_obse") or "",
            }],
        }
        try:
            orc = OrcamentoPisosWebFlowService.criar(banco, payload, request=request)
            messages.success(request, f"Orçamento {orc.orca_nume} criado com sucesso.")
        except Exception as exc:
            messages.error(request, f"Erro ao criar orçamento: {exc}")

    return redirect("PisosWeb:orcamentos_pisos_listar", slug=slug)
