from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_POST
from core.utils import get_licenca_db_config
from GestaoObras.models import Obra
from GestaoObras.services.obras_service import ObrasService


@require_POST
def alterar_status_obra(request, slug, obra_id: int):
    banco = get_licenca_db_config(request)
    obra = get_object_or_404(Obra.objects.using(banco), pk=obra_id)
    novo = request.POST.get("novo_status")
    ObrasService.atualizar_status_obra(banco=banco, obra_id=obra.id, novo_status=novo)
    return redirect("gestaoobras:obras_detail", slug=slug, obra_id=obra.id)
