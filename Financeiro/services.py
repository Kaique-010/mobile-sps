# financeiro/services/orcamento_service.py
from decimal import Decimal
import calendar
from collections import defaultdict
from datetime import date
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce, ExtractMonth
from CentrodeCustos.models import Centrodecustos
from Lancamentos_Bancarios.models import Lctobancario
from .models import Orcamento, OrcamentoItem


class OrcamentoService:
    def __init__(self, *, db_alias: str, empresa_id: int, filial_id: int | None = None):
        self.db = db_alias
        self.empresa_id = empresa_id
        self.filial_id = filial_id

    def _centros_base(self):
        qs = Centrodecustos.objects.using(self.db).filter(
            cecu_empr=self.empresa_id,
        )
        return qs

    def _orcamento_itens_base(self):
        qs = OrcamentoItem.objects.using(self.db).filter(
            orci_empr=self.empresa_id,
        )
        if self.filial_id:
            qs = qs.filter(orci_fili=self.filial_id)
        return qs

    def listar_centros(self):
        return self._centros_base().order_by("cecu_redu")

    def obter_centro(self, cecu_redu: int):
        return self._centros_base().filter(cecu_redu=cecu_redu).first()

    def validar_centro_para_lancamento(self, cecu_redu: int):
        centro = self.obter_centro(cecu_redu)
        if not centro:
            raise ValueError("Centro de custo não encontrado.")
        if centro.cecu_anal != "A":
            raise ValueError("Somente centro de custo analítico pode receber lançamento realizado.")
        return centro

    def salvar_previsto(self, *, orcamento_id: int, centro_custo_id: int, ano: int, mes: int, valor):
        centro = self.obter_centro(centro_custo_id)
        if not centro:
            raise ValueError("Centro de custo não encontrado.")

        item, _ = OrcamentoItem.objects.using(self.db).update_or_create(
            orci_empr=self.empresa_id,
            orci_fili=self.filial_id,
            orci_orca=orcamento_id,
            orci_cecu=centro_custo_id,
            orci_ano=ano,
            orci_mes=mes,
            defaults={
                "orci_valo": valor,
            },
        )
        return item

    def previsto_direto(self, *, orcamento_id: int, centro_custo_id: int, ano: int, mes: int) -> Decimal:
        total = (
            self._orcamento_itens_base()
            .filter(
                orci_orca=orcamento_id,
                orci_cecu=centro_custo_id,
                orci_ano=ano,
                orci_mes=mes,
            )
            .aggregate(total=Sum("orci_valo"))
            .get("total")
        )
        return total or Decimal("0.00")

    def filhos(self, centro_custo_id: int):
        return self._centros_base().filter(cecu_niv1=centro_custo_id).order_by("cecu_redu")

    def centros_analiticos_abaixo(self, centro_custo_id: int):
        filhos = list(self.filhos(centro_custo_id))
        if not filhos:
            centro = self.obter_centro(centro_custo_id)
            if centro and centro.cecu_anal == "A":
                return [centro]
            return []

        resultado = []
        for filho in filhos:
            if filho.cecu_anal == "A":
                resultado.append(filho)
            else:
                resultado.extend(self.centros_analiticos_abaixo(filho.cecu_redu))
        return resultado

    def _cecus_filtro(self, centro_custo_id: int | None):
        if not centro_custo_id:
            return None
        centro = self.obter_centro(int(centro_custo_id))
        if not centro:
            return []
        if getattr(centro, "cecu_anal", None) == "A":
            return [int(centro.cecu_redu)]
        analiticos = self.centros_analiticos_abaixo(int(centro.cecu_redu))
        ids = [int(centro.cecu_redu)]
        ids.extend([int(c.cecu_redu) for c in analiticos])
        return ids

    def previsto_consolidado(self, *, orcamento_id: int, centro_custo_id: int, ano: int, mes: int) -> Decimal:
        centro = self.obter_centro(centro_custo_id)
        if not centro:
            return Decimal("0.00")

        if centro.cecu_anal == "A":
            return self.previsto_direto(
                orcamento_id=orcamento_id,
                centro_custo_id=centro_custo_id,
                ano=ano,
                mes=mes,
            )

        filhos = self.filhos(centro_custo_id)
        total_filhos = Decimal("0.00")
        for filho in filhos:
            total_filhos += self.previsto_consolidado(
                orcamento_id=orcamento_id,
                centro_custo_id=filho.cecu_redu,
                ano=ano,
                mes=mes,
            )

        previsto_do_pai = self.previsto_direto(
            orcamento_id=orcamento_id,
            centro_custo_id=centro_custo_id,
            ano=ano,
            mes=mes,
        )
        return previsto_do_pai + total_filhos

    def realizado_consolidado(self, *, centro_custo_id: int, ano: int, mes: int, dbcr: str = "D") -> Decimal:
        ultimo_dia = calendar.monthrange(int(ano), int(mes))[1]
        inicio = date(int(ano), int(mes), 1)
        fim = date(int(ano), int(mes), int(ultimo_dia))

        qs = Lctobancario.objects.using(self.db).filter(
            laba_empr=int(self.empresa_id),
            laba_cecu=int(centro_custo_id),
        ).filter(Q(laba_data__range=(inicio, fim)) | Q(laba_data_comp__range=(inicio, fim)))
        if self.filial_id:
            qs = qs.filter(laba_fili=int(self.filial_id))

        dbcr = str(dbcr or "").strip().upper()
        if dbcr in ("C", "D"):
            qs = qs.filter(laba_dbcr=dbcr)

        total = qs.aggregate(total=Sum("laba_valo")).get("total")
        return total or Decimal("0.00")

    def resumo_cc(self, *, orcamento_id: int, centro_custo_id: int, ano: int, mes: int, dbcr: str = "D"):
        previsto = self.previsto_consolidado(
            orcamento_id=orcamento_id,
            centro_custo_id=centro_custo_id,
            ano=ano,
            mes=mes,
        )
        realizado = self.realizado_consolidado(
            centro_custo_id=centro_custo_id,
            ano=ano,
            mes=mes,
            dbcr=dbcr,
        )
        saldo = previsto - realizado
        percentual = Decimal("0.00")
        if previsto:
            percentual = (realizado / previsto) * Decimal("100.00")

        centro = self.obter_centro(centro_custo_id)

        return {
            "centro_custo_id": centro_custo_id,
            "centro_custo_nome": getattr(centro, "cecu_nome", ""),
            "tipo": getattr(centro, "cecu_anal", ""),
            "previsto": previsto,
            "realizado": realizado,
            "saldo": saldo,
            "percentual": percentual.quantize(Decimal("0.01")),
        }

    def resumo_raiz(
        self,
        *,
        orcamento_id: int,
        ano: int,
        mes: int,
        expandir: bool = False,
        dbcr: str = "D",
        centro_custo_id: int | None = None,
    ):
        centros = list(
            self._centros_base()
            .values("cecu_redu", "cecu_nome", "cecu_anal", "cecu_niv1")
            .order_by("cecu_redu")
        )
        if not centros:
            return []

        centro_por_id = {int(c["cecu_redu"]): c for c in centros if c.get("cecu_redu") is not None}
        filhos_por_pai = defaultdict(list)
        for c in centros:
            cid = c.get("cecu_redu")
            if cid is None:
                continue
            pai = c.get("cecu_niv1")
            filhos_por_pai[pai].append(int(cid))

        previsto_rows = (
            self._orcamento_itens_base()
            .filter(
                orci_orca=int(orcamento_id),
                orci_ano=int(ano),
                orci_mes=int(mes),
            )
            .values("orci_cecu")
            .annotate(total=Sum("orci_valo"))
        )
        previsto_direto = {int(r["orci_cecu"]): (r["total"] or Decimal("0.00")) for r in previsto_rows if r.get("orci_cecu") is not None}

        ultimo_dia = calendar.monthrange(int(ano), int(mes))[1]
        inicio = date(int(ano), int(mes), 1)
        fim = date(int(ano), int(mes), int(ultimo_dia))

        lcto_qs = Lctobancario.objects.using(self.db).filter(
            laba_empr=int(self.empresa_id),
            laba_cecu__isnull=False,
        ).filter(Q(laba_data__range=(inicio, fim)) | Q(laba_data_comp__range=(inicio, fim)))
        if self.filial_id:
            lcto_qs = lcto_qs.filter(laba_fili=int(self.filial_id))
        dbcr = str(dbcr or "").strip().upper()
        if dbcr in ("C", "D"):
            lcto_qs = lcto_qs.filter(laba_dbcr=dbcr)
        realizado_rows = lcto_qs.values("laba_cecu").annotate(total=Sum("laba_valo"))
        realizado_direto = {int(r["laba_cecu"]): (r["total"] or Decimal("0.00")) for r in realizado_rows if r.get("laba_cecu") is not None}

        consolidado = {}

        def calcular_totais(cid: int):
            if cid in consolidado:
                return consolidado[cid]
            total_prev = previsto_direto.get(cid, Decimal("0.00"))
            total_real = realizado_direto.get(cid, Decimal("0.00"))
            for filho_id in filhos_por_pai.get(cid, []):
                p, r = calcular_totais(int(filho_id))
                total_prev += p
                total_real += r
            consolidado[cid] = (total_prev, total_real)
            return total_prev, total_real

        def linha(cid: int, nivel: int):
            centro = centro_por_id.get(int(cid), {})
            previsto, realizado = calcular_totais(int(cid))
            saldo = previsto - realizado
            percentual = Decimal("0.00")
            if previsto:
                percentual = (realizado / previsto) * Decimal("100.00")
            nome = str(centro.get("cecu_nome") or "")
            prefixo = ("— " * int(nivel)) if nivel else ""
            return {
                "centro_custo_id": int(cid),
                "centro_custo_nome": nome,
                "centro_custo_label": f"{prefixo}{nome}".strip(),
                "tipo": str(centro.get("cecu_anal") or ""),
                "previsto": previsto,
                "realizado": realizado,
                "saldo": saldo,
                "percentual": percentual.quantize(Decimal("0.01")),
                "nivel": int(nivel),
            }

        raizes = filhos_por_pai.get(None, []) + filhos_por_pai.get("", [])
        if centro_custo_id:
            cid = int(centro_custo_id)
            if cid not in centro_por_id:
                return []
            raizes = [cid]
        dados = []

        def dfs(cid: int, nivel: int):
            dados.append(linha(cid, nivel))
            for filho_id in filhos_por_pai.get(cid, []):
                dfs(int(filho_id), nivel + 1)

        if expandir:
            for rid in raizes:
                dfs(int(rid), 0)
            return dados

        for rid in raizes:
            dados.append(linha(int(rid), 0))
        return dados

    def previsto_total_por_mes(self, *, orcamento_id: int, ano: int, centro_custo_id: int | None = None) -> list[Decimal]:
        qs = self._orcamento_itens_base().filter(
            orci_orca=int(orcamento_id),
            orci_ano=int(ano),
        )
        cecus = self._cecus_filtro(centro_custo_id)
        if cecus is not None:
            if not cecus:
                return [Decimal("0.00")] * 12
            qs = qs.filter(orci_cecu__in=cecus)
        rows = qs.values("orci_mes").annotate(total=Sum("orci_valo"))
        mapa = {int(r["orci_mes"]): (r["total"] or Decimal("0.00")) for r in rows if r.get("orci_mes")}
        return [mapa.get(m, Decimal("0.00")) for m in range(1, 13)]

    def realizado_total_por_mes(self, *, ano: int, dbcr: str = "A", centro_custo_id: int | None = None) -> list[Decimal]:
        inicio = date(int(ano), 1, 1)
        fim = date(int(ano), 12, 31)

        qs = Lctobancario.objects.using(self.db).filter(
            laba_empr=int(self.empresa_id),
        )
        if self.filial_id:
            qs = qs.filter(laba_fili=int(self.filial_id))

        dbcr = str(dbcr or "").strip().upper()
        if dbcr in ("C", "D"):
            qs = qs.filter(laba_dbcr=dbcr)

        cecus = self._cecus_filtro(centro_custo_id)
        if cecus is not None:
            if not cecus:
                return [Decimal("0.00")] * 12
            qs = qs.filter(laba_cecu__in=cecus)

        qs = qs.annotate(data_ref=Coalesce("laba_data_comp", "laba_data")).filter(data_ref__range=(inicio, fim))
        rows = qs.annotate(mes=ExtractMonth("data_ref")).values("mes").annotate(total=Sum("laba_valo"))
        mapa = {int(r["mes"]): (r["total"] or Decimal("0.00")) for r in rows if r.get("mes")}
        return [mapa.get(m, Decimal("0.00")) for m in range(1, 13)]

    def evolucao_orcado_realizado(self, *, orcamento_id: int, ano: int, dbcr: str = "A") -> dict:
        orcado = self.previsto_total_por_mes(orcamento_id=orcamento_id, ano=ano)
        realizado = self.realizado_total_por_mes(ano=ano, dbcr=dbcr)
        return {
            "labels": list(range(1, 13)),
            "orcado": [float(v) for v in orcado],
            "realizado": [float(v) for v in realizado],
        }

    def detalhar_realizado(
        self,
        *,
        centro_custo_id: int,
        ano: int,
        mes: int,
        dbcr: str = "A",
        limite: int = 300,
    ) -> list[dict]:
        ultimo_dia = calendar.monthrange(int(ano), int(mes))[1]
        inicio = date(int(ano), int(mes), 1)
        fim = date(int(ano), int(mes), int(ultimo_dia))

        cecus = self._cecus_filtro(int(centro_custo_id))
        if not cecus:
            return []

        qs = Lctobancario.objects.using(self.db).filter(
            laba_empr=int(self.empresa_id),
            laba_cecu__in=cecus,
        )
        if self.filial_id:
            qs = qs.filter(laba_fili=int(self.filial_id))

        dbcr = str(dbcr or "").strip().upper()
        if dbcr in ("C", "D"):
            qs = qs.filter(laba_dbcr=dbcr)

        qs = qs.annotate(data_ref=Coalesce("laba_data_comp", "laba_data")).filter(data_ref__range=(inicio, fim))
        qs = qs.order_by("data_ref", "laba_ctrl")

        rows = list(
            qs.values(
                "laba_ctrl",
                "data_ref",
                "laba_data",
                "laba_data_comp",
                "laba_dbcr",
                "laba_valo",
                "laba_hist",
                "laba_nomi",
                "laba_lote",
                "laba_banc",
                "laba_cont",
                "laba_enti",
                "laba_cecu",
            )[: int(limite)]
        )
        return rows
