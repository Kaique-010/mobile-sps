from django.db import transaction
from CentrodeCustos.models import Centrodecustos
from Financeiro.models import Orcamento
from Financeiro.models import OrcamentoItem


class OrcamentoCadastroService:
    def __init__(self, *, db_alias: str, empresa_id: int, filial_id: int | None = None):
        self.db = db_alias
        self.empresa_id = empresa_id
        self.filial_id = filial_id

    def validar_centro_custo(self, centro_custo_id: int, *, permitir_sintetico: bool = True):
        centro = Centrodecustos.objects.using(self.db).filter(
            cecu_empr=self.empresa_id,
            cecu_redu=centro_custo_id,
        ).first()

        if not centro:
            raise ValueError("Centro de custo não encontrado.")

        if not permitir_sintetico and getattr(centro, "cecu_anal", None) != "A":
            raise ValueError("Somente centro de custo analítico pode receber lançamento de orçamento.")

        return centro

    @transaction.atomic
    def criar_orcamento(self, *, descricao: str, ano: int, tipo: str, cenario: str, ativo: bool = True):
        return Orcamento.objects.using(self.db).create(
            orca_empr=self.empresa_id,
            orca_fili=self.filial_id,
            orca_desc=descricao,
            orca_ano=ano,
            orca_tipo=tipo,
            orca_cena=cenario,
            orca_ativ=ativo,
        )

    @transaction.atomic
    def criar_item(
        self,
        *,
        orcamento_id: int,
        centro_custo_id: int,
        ano: int,
        mes: int,
        valor_previsto,
        observacao: str = "",
    ):
        centro = self.validar_centro_custo(centro_custo_id, permitir_sintetico=False)

        item, _ = OrcamentoItem.objects.using(self.db).update_or_create(
            orci_empr=self.empresa_id,
            orci_fili=self.filial_id,
            orci_orca=orcamento_id,
            orci_cecu=centro.cecu_redu,
            orci_ano=ano,
            orci_mes=mes,
            defaults={
                "orci_valo": valor_previsto,
                "orci_obse": observacao,
            }
        )
        return item

    @transaction.atomic
    def replicar_para_ano_todo(
        self,
        *,
        orcamento_id: int,
        centro_custo_id: int,
        ano: int,
        valor_previsto,
        observacao: str = "",
    ):
        centro = self.validar_centro_custo(centro_custo_id, permitir_sintetico=False)
        itens = []
        for mes in range(1, 13):
            item, _ = OrcamentoItem.objects.using(self.db).update_or_create(
                orci_empr=self.empresa_id,
                orci_fili=self.filial_id,
                orci_orca=orcamento_id,
                orci_cecu=centro.cecu_redu,
                orci_ano=ano,
                orci_mes=mes,
                defaults={
                    "orci_valo": valor_previsto,
                    "orci_obse": observacao,
                }
            )
            itens.append(item)
        return itens

    @transaction.atomic
    def criar_itens_varios_meses(
        self,
        *,
        orcamento_id: int,
        centro_custo_id: int,
        ano: int,
        meses: list[int],
        valor_previsto,
        observacao: str = "",
    ):
        centro = self.validar_centro_custo(centro_custo_id, permitir_sintetico=False)
        meses_ok = []
        for m in (meses or []):
            try:
                mi = int(m)
            except Exception:
                continue
            if 1 <= mi <= 12:
                meses_ok.append(mi)
        meses_ok = sorted(set(meses_ok))
        if not meses_ok:
            return []

        itens = []
        for mes in meses_ok:
            item, _ = OrcamentoItem.objects.using(self.db).update_or_create(
                orci_empr=self.empresa_id,
                orci_fili=self.filial_id,
                orci_orca=orcamento_id,
                orci_cecu=centro.cecu_redu,
                orci_ano=ano,
                orci_mes=mes,
                defaults={
                    "orci_valo": valor_previsto,
                    "orci_obse": observacao,
                }
            )
            itens.append(item)
        return itens

    @transaction.atomic
    def criar_orcamento_com_item_inicial(
        self,
        *,
        descricao: str,
        ano: int,
        tipo: str,
        cenario: str,
        ativo: bool,
        centro_custo_id: int,
        mes: int,
        valor_previsto,
        observacao: str = "",
    ):
        orcamento = self.criar_orcamento(
            descricao=descricao,
            ano=ano,
            tipo=tipo,
            cenario=cenario,
            ativo=ativo,
        )

        item = self.criar_item(
            orcamento_id=orcamento.orca_id,
            centro_custo_id=centro_custo_id,
            ano=ano,
            mes=mes,
            valor_previsto=valor_previsto,
            observacao=observacao,
        )

        return orcamento, item
