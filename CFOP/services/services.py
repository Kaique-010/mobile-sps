from decimal import Decimal, ROUND_HALF_UP
import logging

from ..models import (
    CFOP,
    MapaCFOP,
    TabelaICMS,
    NCM_CFOP_DIF,
)
from Produtos.models import Produtos
from Produtos.models import Ncm
from Produtos.models import NcmAliquota
from Licencas.models import Filiais

def get_empresa_uf_origem(empresa_id: int, filial_id: int | None = None, banco: str | None = None) -> str:
    try:
        qs = Filiais.objects
        if banco:
            qs = qs.using(banco)
        if filial_id is not None:
            f = qs.filter(empr_empr=int(empresa_id), empr_codi=int(filial_id)).first()
        else:
            f = qs.filter(empr_empr=int(empresa_id)).first()
        return (getattr(f, 'empr_esta', '') or '') if f else ''
    except Exception:
        return ''


class MotorFiscal:
    """
    Motor fiscal 2.0
    - Resolve CFOP automático com base em tipo_oper + UF origem/destino
    - Busca NCM e alíquotas padrão (IBPT)
    - Aplica overrides NCM+CFOP
    - Calcula tributos (ICMS/IPI/PIS/COFINS/CBS/IBS)
    """

    def __init__(self, uf_origem: str):
        """
        uf_origem: UF da empresa (ex: 'MA')
        """
        self.uf_origem = uf_origem

    # -----------------------------
    # Helpers internos
    # -----------------------------
    @staticmethod
    def _to_decimal(valor, casas=2):
        if valor is None:
            return None
        if not isinstance(valor, Decimal):
            valor = Decimal(str(valor))
        q = Decimal(10) ** -casas
        return valor.quantize(q, rounding=ROUND_HALF_UP)

    # -----------------------------
    # RESOLVER CFOP AUTOMÁTICO
    # -----------------------------
    def resolver_cfop(self, pedi_tipo_oper: str, uf_destino: str) -> CFOP:
        """
        Retorna o CFOP a partir de:
        - pedi_tipo_oper (VENDA, COMPRA, DEVOLUCAO_VENDA, etc.)
        - uf_origem (do motor)
        - uf_destino (do cliente/fornecedor)
        """
        logging.getLogger(__name__).debug(
            "[MotorFiscal.resolver_cfop] tipo=%s origem=%s destino=%s",
            pedi_tipo_oper, self.uf_origem, uf_destino
        )
        mapa = MapaCFOP.objects.select_related("cfop").get(
            tipo_oper=pedi_tipo_oper,
            uf_origem=self.uf_origem,
            uf_destino=uf_destino,
        )
        return mapa.cfop

    # -----------------------------
    # NCM / ALÍQUOTAS BASE
    # -----------------------------
    def obter_ncm(self, produto: Produtos):
        codigo = (produto.prod_ncm or "").strip()
        if not codigo:
            return None
        try:
            return Ncm.objects.get(ncm_codi=codigo)
        except Ncm.DoesNotExist:
            return None


    def obter_aliquotas_base(self, ncm):
        if ncm is None:
            return {
                "ipi": None,
                "pis": None,
                "cofins": None,
                "cbs": None,
                "ibs": None,
            }

        try:
            aliq = ncm.ncmaliquota
        except NcmAliquota.DoesNotExist:
            return {
                "ipi": None,
                "pis": None,
                "cofins": None,
                "cbs": None,
                "ibs": None,
            }

        return {
            "ipi": self._to_decimal(aliq.aliq_ipi, 2),
            "pis": self._to_decimal(aliq.aliq_pis, 2),
            "cofins": self._to_decimal(aliq.aliq_cofins, 2),
            "cbs": self._to_decimal(aliq.aliq_cbs, 2),
            "ibs": self._to_decimal(aliq.aliq_ibs, 2),
        }



    # -----------------------------
    # ICMS UF_ORIGEM x UF_DESTINO
    # -----------------------------
    def obter_aliquotas_icms(self, uf_destino: str):
        """
        Retorna alíquota de ICMS (interna/inter) e MVA ST (se houver).
        """
        try:
            tab = TabelaICMS.objects.get(
                uf_origem=self.uf_origem,
                uf_destino=uf_destino,
            )
        except TabelaICMS.DoesNotExist:
            return {
                "icms": None,
                "mva_st": None,
            }

        mesma_uf = self.uf_origem == uf_destino
        aliq_icms = tab.aliq_interna if mesma_uf else tab.aliq_inter

        return {
            "icms": self._to_decimal(aliq_icms, 2),
            "mva_st": self._to_decimal(tab.mva_st, 2),
        }

    # -----------------------------
    # OVERRIDES NCM + CFOP
    # -----------------------------
    def aplicar_overrides_ncm_cfop(self, ncm, cfop: CFOP, aliquotas: dict, icms_data: dict):
        """
        Aplica diferenciais definidos em NCM_CFOP_DIF, se existirem.
        - aliquotas: dict das alíquotas base (ipi/pis/cofins/cbs/ibs)
        - icms_data: dict icms/mva_st
        Retorna (aliquotas_atualizadas, icms_data_atualizada)
        """
        if ncm is None:
            return aliquotas, icms_data

        try:
            dif = NCM_CFOP_DIF.objects.get(ncm=ncm, cfop=cfop)
        except NCM_CFOP_DIF.DoesNotExist:
            return aliquotas, icms_data

        # substitui só o que tiver preenchido
        if dif.ncm_ipi_dif is not None:
            aliquotas["ipi"] = self._to_decimal(dif.ncm_ipi_dif, 2)
        if dif.ncm_pis_dif is not None:
            aliquotas["pis"] = self._to_decimal(dif.ncm_pis_dif, 2)
        if dif.ncm_cofins_dif is not None:
            aliquotas["cofins"] = self._to_decimal(dif.ncm_cofins_dif, 2)
        if dif.ncm_cbs_dif is not None:
            aliquotas["cbs"] = self._to_decimal(dif.ncm_cbs_dif, 2)
        if dif.ncm_ibs_dif is not None:
            aliquotas["ibs"] = self._to_decimal(dif.ncm_ibs_dif, 2)

        if dif.ncm_icms_aliq_dif is not None:
            icms_data["icms"] = self._to_decimal(dif.ncm_icms_aliq_dif, 2)
        if dif.ncm_st_aliq_dif is not None:
            icms_data["st_aliq"] = self._to_decimal(dif.ncm_st_aliq_dif, 2)
        else:
            icms_data.setdefault("st_aliq", None)

        return aliquotas, icms_data

    # -----------------------------
    # CÁLCULO TRIBUTOS
    # -----------------------------
    def calcular_bases(self, item) -> Decimal:
        """
        Determina a base de cálculo (valor total do item).
        item: Itenspedidovenda
        """
        # prioridade: total informado > (quantidade * unitário)
        if item.iped_tota is not None:
            return self._to_decimal(item.iped_tota, 2)

        quant = self._to_decimal(item.iped_quan or 0, 5)
        unit = self._to_decimal(item.iped_unit or 0, 5)
        total = quant * unit
        return self._to_decimal(total, 2)

    def calcular_valor(self, base: Decimal, aliquota):
        if base is None or aliquota is None:
            return None
        return self._to_decimal(base * (aliquota / Decimal("100")), 2)

    # -----------------------------
    # MÉTODO PRINCIPAL: CALCULAR ITEM
    # -----------------------------
    def calcular_item(
        self,
        pedido,
        item,
        produto: Produtos,
        uf_destino: str,
        pedi_tipo_oper: str,
    ):
        """
        Calcula o pacote fiscal completo de um item.
        - pedido: PedidoVenda (usa pedido.tipo_oper)
        - item: Itenspedidovenda
        - produto: Produtos
        - uf_destino: UF do cliente
        Retorna um dict com:
            - cfop
            - bases
            - alíquotas
            - valores de cada tributo
        """

        logging.getLogger(__name__).debug(
            "[MotorFiscal.calcular_item] uf_origem=%s uf_destino=%s tipo=%s produto=%s",
            self.uf_origem, uf_destino, pedi_tipo_oper, getattr(produto, 'prod_codi', None)
        )
        # 1) Resolve CFOP automático
        cfop = self.resolver_cfop(pedi_tipo_oper=pedi_tipo_oper, uf_destino=uf_destino)

        # 2) Resolve NCM e alíquotas base
        ncm = self.obter_ncm(produto)
        aliquotas = self.obter_aliquotas_base(ncm)

        # 3) ICMS / ST
        icms_data = self.obter_aliquotas_icms(uf_destino=uf_destino)

        # 4) Overrides NCM + CFOP
        aliquotas, icms_data = self.aplicar_overrides_ncm_cfop(ncm, cfop, aliquotas, icms_data)

        # 5) Base de cálculo
        base = self.calcular_bases(item)

        # 6) Calcula tributos
        valor_ipi = self.calcular_valor(base, aliquotas["ipi"]) if cfop.cfop_exig_ipi else None
        valor_icms = self.calcular_valor(base, icms_data.get("icms")) if cfop.cfop_exig_icms else None
        valor_pis = self.calcular_valor(base, aliquotas["pis"]) if cfop.cfop_exig_pis_cofins else None
        valor_cofins = self.calcular_valor(base, aliquotas["cofins"]) if cfop.cfop_exig_pis_cofins else None

        # ST – se cfop_gera_st estiver marcado e tiver aliquota ST definida
        st_aliq = icms_data.get("st_aliq") or None
        valor_st = None
        if cfop.cfop_gera_st and st_aliq is not None:
            valor_st = self.calcular_valor(base, st_aliq)

        # Aqui dá pra incluir CBS/IBS se quiser já com valores
        valor_cbs = self.calcular_valor(base, aliquotas.get("cbs")) if getattr(cfop, 'cfop_exig_cbs', False) else None
        valor_ibs = self.calcular_valor(base, aliquotas.get("ibs")) if getattr(cfop, 'cfop_exig_ibs', False) else None

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

    def aplicar_no_item(self, item, pacote):
        """
        Preenche TODOS os campos fiscais do Itenspedidovenda
        usando o pacote fiscal calculado.
        """

        # Base
        item.iped_base_icms = pacote["base_calculo"]

        # Alíquotas
        item.iped_pipi = pacote["aliquotas"]["ipi"]
        item.iped_aliq_icms = pacote["aliquotas"]["icms"]
        item.iped_aliq_icms_st = pacote["aliquotas"]["st_aliq"]
        item.iped_aliq_pis = pacote["aliquotas"]["pis"]
        item.iped_aliq_cofi = pacote["aliquotas"]["cofins"]

        # Valores
        item.iped_vipi = pacote["valores"]["ipi"]
        item.iped_valo_icms = pacote["valores"]["icms"]
        item.iped_valo_icms_st = pacote["valores"]["st"]
        item.iped_valo_pis = pacote["valores"]["pis"]
        item.iped_valo_cofi = pacote["valores"]["cofins"]

        # Bases PIS/COFINS
        item.iped_base_pis = pacote["base_calculo"]
        item.iped_base_cofi = pacote["base_calculo"]

        # Já deixa CST genérico (pode evoluir depois)
        if pacote["aliquotas"]["icms"]:
            item.iped_cst_icms = "000"
        if pacote["aliquotas"]["pis"]:
            item.iped_cst_pis = "01"
        if pacote["aliquotas"]["cofins"]:
            item.iped_cst_cofi = "01"

        return item
