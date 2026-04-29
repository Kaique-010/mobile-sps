import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from core.utils import get_db_from_slug
from Pisos.models import Orcamentopisos
from Pisos.services.web_flow_service import exportar_orcamento_para_pedido


logger = logging.getLogger(__name__)


def exportar_orcamento_pedido(request, slug, numero):
    banco = get_db_from_slug(slug)
    orcamento = get_object_or_404(Orcamentopisos.objects.using(banco), orca_nume=numero)
    try:
        pedido_numero = exportar_orcamento_para_pedido(banco, orcamento.orca_empr, orcamento.orca_fili, orcamento.orca_nume)
        messages.success(request, f"Orçamento {numero} exportado para pedido {pedido_numero}.")
        return redirect("PisosWeb:pedidos_pisos_visualizar", slug=slug, pk=pedido_numero)
    except Exception as exc:
        logger.exception("Erro ao exportar orçamento para pedido (slug=%s, banco=%s, orca=%s).", slug, banco, numero)
        messages.error(request, f"Erro ao exportar orçamento: {exc}")
        return redirect("PisosWeb:orcamentos_pisos_visualizar", slug=slug, pk=numero)

