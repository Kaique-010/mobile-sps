from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from core.utils import get_db_from_slug
from Pisos.models import Orcamentopisos
from Pisos.services.web_flow_service import exportar_orcamento_para_pedido


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
