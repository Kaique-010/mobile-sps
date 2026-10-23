# entidades/services/relatorio.py
from django.db.models import Count, Q
from django.db.models.functions import ExtractDay, ExtractMonth

from ..models import Entidades


class EntidadesRelatorioService:
    """
    Regras do relatório de entidades.

    Filtros combináveis:
      - empresa  : código da empresa ('' = todas, 'Outros' = sem empresa)
      - meses    : lista de meses de aniversário (1-12)
      - busca    : nome / número / código
      - situacao : '1' ativos | '0' inativos   (afeta gráfico de tipos e lista)
      - tipo     : enti_tipo_enti               (afeta só a lista)

    KPIs (ativos/inativos) ignoram situacao e tipo, para sempre mostrar os dois lados.
    """

    LIMITE_LISTA = 500

    CAMPOS_LISTA = (
        "enti_clie",
        "enti_nome",
        "enti_dana",
        "enti_tipo_enti",
        "enti_emai",
        "enti_fone",
        "enti_celu",
        "enti_cida",
        "enti_esta",
        "enti_situ",
    )

    _SITUACOES = {
        "1": "1", "ativo": "1", "ativos": "1",
        "0": "0", "inativo": "0", "inativos": "0",
    }

    @classmethod
    def normalizar_situacao(cls, valor):
        valor = (valor or "").strip().lower()
        if not valor:
            return None
        if valor not in cls._SITUACOES:
            raise ValueError("Situação inválida. Use 1 (ativos) ou 0 (inativos).")
        return cls._SITUACOES[valor]

    @staticmethod
    def normalizar_meses(valor):
        if not valor:
            return []
        meses = set()
        for parte in str(valor).split(","):
            parte = parte.strip()
            if not parte:
                continue
            try:
                mes = int(parte)
            except ValueError:
                raise ValueError("Mês inválido. Informe valores entre 1 e 12.")
            if not 1 <= mes <= 12:
                raise ValueError("Mês inválido. Informe valores entre 1 e 12.")
            meses.add(mes)
        return sorted(meses)

    @classmethod
    def _queryset_base(cls, banco, empresa, meses, busca):
        qs = Entidades.objects.using(banco).all()

        empresa = (str(empresa).strip() if empresa is not None else "")
        if empresa == "Outros":
            qs = qs.filter(enti_empr__isnull=True)
        elif empresa:
            qs = qs.filter(enti_empr=empresa)

        if meses:
            qs = qs.filter(enti_dana__isnull=False, enti_dana__month__in=meses)

        busca = (busca or "").strip()
        if busca:
            filtro = Q(enti_nome__icontains=busca) | Q(enti_nume__icontains=busca)
            if busca.isdigit():
                filtro |= Q(enti_clie=int(busca))
            qs = qs.filter(filtro)

        return qs

    @classmethod
    def gerar(cls, banco, empresa=None, situacao=None, meses=None, tipo=None, busca=None):
        base = cls._queryset_base(banco, empresa, meses, busca)

        totais = base.aggregate(
            ativos=Count("enti_clie", filter=Q(enti_situ="1")),
            inativos=Count("enti_clie", filter=Q(enti_situ="0")),
        )

        com_situacao = base.filter(enti_situ=situacao) if situacao else base

        por_tipo = list(
            com_situacao.values("enti_tipo_enti")
            .annotate(total=Count("enti_clie"))
            .order_by("-total")
        )

        lista = com_situacao.filter(enti_tipo_enti=tipo) if tipo else com_situacao
        total_listado = lista.count()

        if meses:
            lista = lista.annotate(
                mes_aniv=ExtractMonth("enti_dana"),
                dia_aniv=ExtractDay("enti_dana"),
            ).order_by("mes_aniv", "dia_aniv", "enti_nome")
        else:
            lista = lista.order_by("enti_nome")

        entidades = list(lista.values(*cls.CAMPOS_LISTA)[: cls.LIMITE_LISTA])

        return {
            "ativos": totais["ativos"],
            "inativos": totais["inativos"],
            "total": totais["ativos"] + totais["inativos"],
            "por_tipo": por_tipo,
            "entidades": entidades,
            "total_listado": total_listado,
            "limitado": total_listado > cls.LIMITE_LISTA,
            "filtros": {
                "empresa": empresa or "",
                "situacao": situacao or "",
                "meses": meses or [],
                "tipo": tipo or "",
                "busca": busca or "",
            },
        }