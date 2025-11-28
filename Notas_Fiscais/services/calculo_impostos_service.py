from decimal import Decimal
from django.db import transaction

from ..models import Nota, NotaItem, NotaItemImposto
from Licencas.models import Filiais
from Entidades.models import Entidades
from Produtos.models import Produtos
from CFOP.services.services import MotorFiscal, get_empresa_uf_origem


class CalculoImpostosService:
    """
    Calcula e aplica impostos para uma Nota:
    - Usa MotorFiscal (já existente) para resolver CFOP, NCM, alíquotas etc.
    - Preenche NotaItemImposto item a item.
    - Opcionalmente ajusta CFOP e CSTs dos itens se estiverem em branco.
    """

    def __init__(self, database: str = "default"):
        self.database = database

    # ------------------------------------------------------------------
    # PÚBLICO: aplica em uma nota inteira
    # ------------------------------------------------------------------
    def aplicar_impostos(self, nota: Nota):
        """
        Calcula e aplica impostos para todos os itens da nota.
        """
        # Garante que estamos usando o banco correto
        nota = Nota.objects.using(self.database).get(pk=nota.pk)

        uf_origem = get_empresa_uf_origem(
            empresa_id=nota.empresa,
            filial_id=nota.filial,
            banco=self.database,
        )

        uf_destino = (nota.destinatario.enti_esta or "").strip()

        motor = MotorFiscal(uf_origem=uf_origem, database=self.database)
        tipo_oper = self._mapear_tipo_operacao(nota)

        itens = (
            NotaItem.objects.using(self.database)
            .select_related("produto")
            .filter(nota=nota)
        )

        with transaction.atomic(using=self.database):
            for item in itens:
                pacote = self._calcular_pacote_item(
                    motor=motor,
                    nota=nota,
                    item=item,
                    uf_destino=uf_destino,
                    pedi_tipo_oper=tipo_oper,
                )
                self._aplicar_no_item_nota(item, pacote)

    # ------------------------------------------------------------------
    # MAPEAMENTO DE TIPO OPERAÇÃO (nota → MotorFiscal / MapaCFOP)
    # ------------------------------------------------------------------
    def _mapear_tipo_operacao(self, nota: Nota) -> str:
        """
        Traduz o tipo_operacao da Nota (0/1) + finalidade em algo que
        o MapaCFOP entende (VENDA, COMPRA, DEVOLUCAO_VENDA, etc.).
        Ajuste aqui se você tiver mais granularidade depois.
        """
        # 0 = Entrada, 1 = Saída
        if nota.tipo_operacao == 1:  # Saída
            if nota.finalidade == 4:  # Devolução
                return "DEVOLUCAO_COMPRA"
            return "VENDA"
        else:  # Entrada
            if nota.finalidade == 4:
                return "DEVOLUCAO_VENDA"
            return "COMPRA"

    # ------------------------------------------------------------------
    # CÁLCULO DO PACOTE FISCAL PARA UM ITEM DA NOTA
    # ------------------------------------------------------------------
    def _calcular_pacote_item(
        self,
        motor: MotorFiscal,
        nota: Nota,
        item: NotaItem,
        uf_destino: str,
        pedi_tipo_oper: str,
    ) -> dict:
        """
        Replica a lógica do MotorFiscal.calcular_item, mas adaptado
        para Nota/NotaItem em vez de Pedido/Itenspedidovenda.
        """

        produto: Produtos = item.produto

        # 1) CFOP
        from CFOP.models import CFOP

        cfop = None
        if item.cfop:
            cfop = (
                CFOP.objects.using(self.database)
                .filter(cfop_codi=item.cfop, cfop_empr=nota.empresa)
                .first()
            )
        if not cfop:
            cfop = (
                CFOP.objects.using(self.database)
                .filter(cfop_empr=nota.empresa, cfop_codi__in=["5102", "5101", "6102", "6101"])
                .order_by("cfop_codi")
                .first()
            )
            if cfop:
                item.cfop = cfop.cfop_codi
            else:
                from types import SimpleNamespace
                codigo = item.cfop or "5102"
                cfop = SimpleNamespace(
                    cfop_codi=codigo,
                    cfop_exig_ipi=False,
                    cfop_exig_icms=True,
                    cfop_exig_pis_cofins=True,
                    cfop_exig_cbs=False,
                    cfop_exig_ibs=False,
                    cfop_gera_st=False,
                )

        # 2) NCM e alíquotas base (IBPT)
        ncm = motor.obter_ncm(produto)
        aliquotas = motor.obter_aliquotas_base(ncm)

        # 3) ICMS UF origem x destino
        icms_data = motor.obter_aliquotas_icms(uf_destino=uf_destino, empresa=nota.empresa, banco=self.database)

        # 4) Overrides NCM + CFOP
        if isinstance(cfop, CFOP):
            aliquotas, icms_data = motor.aplicar_overrides_ncm_cfop(ncm, cfop, aliquotas, icms_data)

        # 5) Base de cálculo NF: usa total se tiver, senão quantidade*unitário - desconto
        base = self._calcular_base_nota_item(motor, item)

        # 6) Cálculo dos tributos (mesma ideia do MotorFiscal.calcular_item)
        valor_ipi = motor.calcular_valor(base, aliquotas["ipi"]) if getattr(cfop, "cfop_exig_ipi", False) else None
        valor_icms = motor.calcular_valor(base, icms_data.get("icms")) if getattr(cfop, "cfop_exig_icms", False) else None
        valor_pis = motor.calcular_valor(base, aliquotas["pis"]) if getattr(cfop, "cfop_exig_pis_cofins", False) else None
        valor_cofins = motor.calcular_valor(base, aliquotas["cofins"]) if getattr(cfop, "cfop_exig_pis_cofins", False) else None

        # ST – se marcado e existir aliquota ST
        st_aliq = icms_data.get("st_aliq") or None
        valor_st = None
        if getattr(cfop, "cfop_gera_st", False) and st_aliq is not None:
            valor_st = motor.calcular_valor(base, st_aliq)

        valor_cbs = motor.calcular_valor(base, aliquotas.get("cbs")) if getattr(cfop, "cfop_exig_cbs", False) else None
        valor_ibs = motor.calcular_valor(base, aliquotas.get("ibs")) if getattr(cfop, "cfop_exig_ibs", False) else None

        return {
            "cfop_codigo": cfop.cfop_codi,
            "cfop_obj": cfop,
            "base_calculo": base,
            "aliquotas": {
                "ipi": aliquotas["ipi"],
                "icms": icms_data.get("icms"),
                "st_aliq": st_aliq,
                "pis": aliquotas["pis"],
                "cofins": aliquotas["cofins"],
                "cbs": aliquotas["cbs"],
                "ibs": aliquotas["ibs"],
            },
            "valores": {
                "ipi": valor_ipi,
                "icms": valor_icms,
                "st": valor_st,
                "pis": valor_pis,
                "cofins": valor_cofins,
                "cbs": valor_cbs,
                "ibs": valor_ibs,
            },
        }

    def _calcular_base_nota_item(self, motor: MotorFiscal, item: NotaItem) -> Decimal:
        """
        Base de cálculo para NF:
        - se NotaItem.total preenchido, usa ele
        - senão: (quantidade * unitario) - desconto
        Usa o _to_decimal do MotorFiscal para padronizar.
        """
        if item.total is not None:
            return motor._to_decimal(item.total, 2)

        quant = motor._to_decimal(item.quantidade or 0, 5)
        unit = motor._to_decimal(item.unitario or 0, 5)
        desc = motor._to_decimal(item.desconto or 0, 5)

        total = (quant * unit) - desc
        return motor._to_decimal(total, 2)

    # ------------------------------------------------------------------
    # PERSISTÊNCIA EM NotaItem + NotaItemImposto
    # ------------------------------------------------------------------
    def _aplicar_no_item_nota(self, item: NotaItem, pacote: dict):
        """
        Aplica o pacote fiscal calculado no:
        - NotaItemImposto (tabela nf_item_imposto)
        - Opcionalmente ajusta CSTs e CFOP do item
        """
        # Atualiza CFOP do item, se ainda não tiver
        if not item.cfop:
            item.cfop = pacote["cfop_codigo"]

        # Opcional: ajustar CSTs default, se ainda não vierem preenchidos
        if not item.cst_icms and pacote["aliquotas"]["icms"]:
            item.cst_icms = "000"
        if not item.cst_pis and pacote["aliquotas"]["pis"]:
            item.cst_pis = "01"
        if not item.cst_cofins and pacote["aliquotas"]["cofins"]:
            item.cst_cofins = "01"

        item.save(using=self.database)

        # Impostos do item
        imp, _ = NotaItemImposto.objects.using(self.database).get_or_create(item=item)

        base = pacote["base_calculo"]
        aliq = pacote["aliquotas"]
        val = pacote["valores"]

        imp.icms_base = base
        imp.icms_aliquota = aliq["icms"]
        imp.icms_valor = val["icms"]

        imp.ipi_valor = val["ipi"]
        imp.pis_valor = val["pis"]
        imp.cofins_valor = val["cofins"]

        # FCP: por enquanto deixamos None, a não ser que você passe a calcular
        imp.fcp_valor = None

        # CBS / IBS: se quiser já armazenar
        imp.cbs_base = base if aliq["cbs"] is not None else None
        imp.cbs_aliquota = aliq["cbs"]
        imp.cbs_valor = val["cbs"]

        imp.ibs_base = base if aliq["ibs"] is not None else None
        imp.ibs_aliquota = aliq["ibs"]
        imp.ibs_valor = val["ibs"]

        imp.save(using=self.database)
