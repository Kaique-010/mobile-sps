from django.shortcuts import render
from decimal import Decimal
from core.utils import get_licenca_db_config
from GestaoObras.models import Obra
from Entidades.models import Entidades

def listar_obras(request, slug):
    banco = get_licenca_db_config(request)
    empresa = request.GET.get("empr") or request.headers.get("X-Empresa")
    filial = request.GET.get("fili") or request.headers.get("X-Filial")
    filtro = (request.GET.get("f") or "").strip().lower()
    mapa = {
        "planejadas": "PL",
        "em-andamento": "EA",
        "paralisadas": "PA",
        "concluidas": "CO",
        "canceladas": "CA",
    }
    qs = Obra.objects.using(banco)
    if empresa and filial:
        qs = qs.filter(obra_empr=empresa, obra_fili=filial)
    if filtro in mapa:
        qs = qs.filter(obra_stat=mapa[filtro])
    total = qs.count()
    try:
        clientes_ids = list(qs.values_list("obra_clie", flat=True))
        if clientes_ids:
            ent_qs = Entidades.objects.using(banco).filter(enti_clie__in=clientes_ids)
            if empresa:
                ent_qs = ent_qs.filter(enti_empr=int(empresa))
            nomes_map = {e.enti_clie: (e.enti_nome or "") for e in ent_qs}
            for o in qs:
                o.obra_cliente_nome = nomes_map.get(o.obra_clie, "")
    except Exception:
        for o in qs:
            o.obra_cliente_nome = ""
    alertas = []
    total_orcamento = Decimal("0")
    total_custo = Decimal("0")
    for o in qs:
        orcamento = float(o.obra_orca or 0)
        custo = float(o.obra_cust or 0)
        try:
            total_orcamento += Decimal(str(o.obra_orca or 0))
            total_custo += Decimal(str(o.obra_cust or 0))
        except Exception:
            pass
        perc = 0.0
        if orcamento > 0:
            perc = (custo / orcamento) * 100.0
        o.orcamento_perc = perc
        if orcamento <= 0:
            o.orcamento_class = "text-muted"
        elif perc < 80:
            o.orcamento_class = "text-success fw-bold"
        elif perc < 90:
            o.orcamento_class = "text-warning fw-bold"
        elif perc < 100:
            o.orcamento_class = "text-warning fw-bold"
            alertas.append(f"{o.obra_codi} - {o.obra_nome}")
        else:
            o.orcamento_class = "text-danger fw-bold"
            alertas.append(f"{o.obra_codi} - {o.obra_nome}")
    base = Obra.objects.using(banco)
    if empresa and filial:
        base = base.filter(obra_empr=empresa, obra_fili=filial)
    tot_pl = base.filter(obra_stat="PL").count()
    tot_ea = base.filter(obra_stat="EA").count()
    tot_pa = base.filter(obra_stat="PA").count()
    tot_co = base.filter(obra_stat="CO").count()
    tot_ca = base.filter(obra_stat="CA").count()
    ctx = {
        "slug": slug,
        "obras": qs,
        "total_obras": base.count(),
        "total_planejadas": tot_pl,
        "total_em_andamento": tot_ea,
        "total_paralisadas": tot_pa,
        "total_concluidas": tot_co,
        "total_canceladas": tot_ca,
        "f": filtro,
        "obras_alertas": alertas,
        "total_orcamento": total_orcamento,
        "total_custo": total_custo,
        "percentual_custo": float((total_custo / total_orcamento) * 100) if total_orcamento > 0 else 0.0,
    }
    return render(request, "obras/listar.html", ctx)
