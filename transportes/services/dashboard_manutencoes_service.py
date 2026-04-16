from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from transportes.models import Abastecusto, Custos, Veiculos
from transportes.services.servico_de_abastecimento import AbastecimentoService
from transportes.services.servico_de_lancamento_custos import LancamentoCustosService


@dataclass
class DashboardFiltros:
    frota: str = ""
    veiculo: str = ""


class DashboardManutencoesService:
    """Serviço agregador para histórico de manutenções e abastecimentos por frota/veículo."""

    def __init__(
        self,
        abastecimento_service=AbastecimentoService,
        lancamento_custos_service=LancamentoCustosService,
    ):
        self.abastecimento_service = abastecimento_service
        self.lancamento_custos_service = lancamento_custos_service

    def _base_abastecimentos(self, *, using: str, empresa_id: int, filial_id: int | None):
        qs = Abastecusto.objects.using(using).filter(abas_empr=empresa_id)
        if filial_id:
            qs = qs.filter(abas_fili=filial_id)
        return qs

    def _base_custos(self, *, using: str, empresa_id: int, filial_id: int | None):
        qs = Custos.objects.using(using).filter(lacu_empr=empresa_id)
        if filial_id:
            qs = qs.filter(lacu_fili=filial_id)
        return qs

    def listar_frotas(self, *, using: str, empresa_id: int, filial_id: int | None):
        custos_frotas = {
            str(item).strip()
            for item in self._base_custos(using=using, empresa_id=empresa_id, filial_id=filial_id)
            .values_list("lacu_frot", flat=True)
            if item
        }
        abaste_frotas = {
            str(item).strip()
            for item in self._base_abastecimentos(using=using, empresa_id=empresa_id, filial_id=filial_id)
            .values_list("abas_frot", flat=True)
            if item
        }
        return sorted(custos_frotas | abaste_frotas)

    def listar_veiculos(self, *, using: str, empresa_id: int, frota: str | None = None):
        qs = Veiculos.objects.using(using).filter(veic_empr=empresa_id)
        if frota:
            try:
                qs = qs.filter(veic_tran=int(frota))
            except (TypeError, ValueError):
                return []

        veiculos = []
        for item in qs.order_by("veic_tran", "veic_sequ"):
            veiculos.append(
                {
                    "sequencial": item.veic_sequ,
                    "frota": item.veic_tran,
                    "placa": item.veic_plac,
                    "descricao": f"{item.veic_tran} / {item.veic_sequ} - {item.veic_plac or '-'}",
                }
            )
        return veiculos

    def buscar_movimentacoes(
        self,
        *,
        using: str,
        empresa_id: int,
        filial_id: int | None,
        filtros: DashboardFiltros,
    ):
        custos_qs = self._base_custos(using=using, empresa_id=empresa_id, filial_id=filial_id)
        abaste_qs = self._base_abastecimentos(using=using, empresa_id=empresa_id, filial_id=filial_id)

        if filtros.frota:
            custos_qs = custos_qs.filter(lacu_frot=filtros.frota)
            abaste_qs = abaste_qs.filter(abas_frot=filtros.frota)

        if filtros.veiculo:
            try:
                veiculo = int(filtros.veiculo)
            except (TypeError, ValueError):
                veiculo = None
            if veiculo is not None:
                custos_qs = custos_qs.filter(lacu_veic=veiculo)
                abaste_qs = abaste_qs.filter(abas_veic_sequ=veiculo)

        movimentacoes = []
        for item in custos_qs.order_by("-lacu_data", "-lacu_ctrl")[:200]:
            movimentacoes.append(
                {
                    "tipo": "Manutenção/Custo",
                    "data": item.lacu_data,
                    "frota": item.lacu_frot,
                    "veiculo": item.lacu_veic,
                    "descricao": item.lacu_nome_item or item.lacu_item,
                    "documento": item.lacu_docu,
                    "valor": item.lacu_tota or Decimal("0"),
                    "controle": item.lacu_ctrl,
                }
            )

        for item in abaste_qs.order_by("-abas_data", "-abas_ctrl")[:200]:
            movimentacoes.append(
                {
                    "tipo": "Abastecimento",
                    "data": item.abas_data,
                    "frota": item.abas_frot,
                    "veiculo": item.abas_veic_sequ,
                    "descricao": item.abas_comb,
                    "documento": item.abas_docu,
                    "valor": item.abas_tota or Decimal("0"),
                    "controle": item.abas_ctrl,
                }
            )

        movimentacoes.sort(key=lambda mov: (mov.get("data") is not None, mov.get("data")), reverse=True)

        total_custos = sum((mov["valor"] for mov in movimentacoes if mov["tipo"] == "Manutenção/Custo"), Decimal("0"))
        total_abastecimentos = sum((mov["valor"] for mov in movimentacoes if mov["tipo"] == "Abastecimento"), Decimal("0"))

        return {
            "movimentacoes": movimentacoes,
            "total_movimentacoes": len(movimentacoes),
            "total_custos": total_custos,
            "total_abastecimentos": total_abastecimentos,
            "service_origem": {
                "abastecimento": self.abastecimento_service.__name__,
                "lancamento_custos": self.lancamento_custos_service.__name__,
            },
        }
