from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from Entidades.models import Entidades

from conciliacao.contexto import obter_contexto
from conciliacao.models import ConciliacaoHist, ItemExtrato
from conciliacao.services.conciliar import ConciliarExtratoService
 
 
@login_required
@require_GET
def detalhe_vinculos(request, slug, empresa, filial, numero, item_id):
 
    ctx = obter_contexto(request, slug, acao="view")
 
    if empresa != ctx.empresa or filial != ctx.filial:
        return JsonResponse({"erro": "Sem acesso."}, status=403)
 
    item = (
        ItemExtrato.objects
        .using(ctx.db_alias)
        .filter(
            id=item_id,
            nume=numero,
            empresa=ctx.empresa,
            filial=ctx.filial,
        )
        .first()
    )
 
    if not item:
        return JsonResponse({"erro": "Item não encontrado."}, status=404)
    
    service = ConciliarExtratoService(
        banco=ctx.db_alias,
        empresa=ctx.empresa,
        filial=ctx.filial,
        numero=numero,
    )
    status = service._status_conciliacao(item)
 
    vinculos = (
        ConciliacaoHist.objects
        .filter(
            nume=numero,
            empresa=ctx.empresa,
            filial=ctx.filial,
            item_extrato=item.id,
        )
        .order_by("data")
    )
    
    resultado = []
 
    for v in vinculos:
        nome_entidade = "Desconhecida"
        if v.entidade:
            nome_entidade = Entidades.objects.get(enti_clie=v.entidade).enti_nome
        resultado.append({
            "id": v.id,
            "origem": v.origem,
            "titulo": v.titulo,
            "entidade": nome_entidade,
            "serie": v.serie,
            "parcela": v.parcela,
            "valor": str(v.valor),
            "controle_bancario": v.controle_bancario,
            "data": v.data.strftime("%d/%m/%Y %H:%M"),
        })
 
    return JsonResponse({
        "item_id": item.id,
        "valor_extrato": str(item.valor),
        "vinculos": resultado,
        "total_vinculado": str(status["total_vinculado"]),
        "saldo": str(status["saldo"]),
    })
 