from decimal import Decimal, ROUND_HALF_UP
import logging
from ..models import CFOP, MapaCFOP, TabelaICMS, NCM_CFOP_DIF
from Produtos.models import Produtos, Ncm, NcmAliquota
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
    - Resolve CFOP automático com base em tipo_oper + UF origem/destino
    - Busca NCM e alíquotas padrão (IBPT)
    - Aplica overrides NCM+CFOP
    - Calcula tributos (ICMS/IPI/PIS/COFINS/CBS/IBS)
    """

    def __init__(self, uf_origem: str, database: str | None = None):
        """
        uf_origem: UF da empresa (ex: 'MA')
        database: alias do banco para consultas multi-tenant
        """
        self.uf_origem = uf_origem
        self.database = database

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
    
    def calcular_valor(self, base: Decimal, aliquota):
        if base is None or aliquota is None:
            return None
        return self._to_decimal(base * (aliquota / Decimal("100")), 2)

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
        qs = MapaCFOP.objects
        if self.database:
            qs = qs.using(self.database)
        mapa = qs.select_related("cfop").get(
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
            qs = Ncm.objects
            if self.database:
                qs = qs.using(self.database)
            return qs.get(ncm_codi=codigo)
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
    def obter_aliquotas_icms(self, uf_destino: str, empresa: int | None = None, banco: str | None = None):
        """
        Retorna alíquota de ICMS (interna/inter) e MVA ST (se houver).
        """
        qs = TabelaICMS.objects
        if banco:
            qs = qs.using(banco)
        filtro = {
            'uf_origem': self.uf_origem,
            'uf_destino': uf_destino,
        }
        if empresa is not None:
            filtro['empresa'] = int(empresa)

        tab = qs.filter(**filtro).values('aliq_interna', 'aliq_inter', 'mva_st').order_by('empresa').first()
        if not tab:
            return {
                "icms": None,
                "mva_st": None,
            }

        mesma_uf = self.uf_origem == uf_destino
        aliq_icms = tab['aliq_interna'] if mesma_uf else tab['aliq_inter']

        return {
            "icms": self._to_decimal(aliq_icms, 2),
            "mva_st": self._to_decimal(tab['mva_st'], 2),
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
            qs = NCM_CFOP_DIF.objects
            if self.database:
                qs = qs.using(self.database)
            dif = qs.get(ncm=ncm, cfop=cfop)
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
    # Bases
    # -----------------------------
    def calcular_base_raiz(self, item):
        if item.iped_tota is not None:
            return self._to_decimal(item.iped_tota)
        return self._to_decimal(
            self._to_decimal(item.iped_quan, 5) * self._to_decimal(item.iped_unit, 5)
        )

    def calcular_bases_icms_st(self, base_raiz, valor_ipi, cfop):
        base_icms = base_raiz
        if cfop.cfop_icms_base_inclui_ipi and valor_ipi:
            base_icms += valor_ipi

        base_st = base_icms
        if cfop.cfop_st_base_inclui_ipi and valor_ipi:
            base_st += valor_ipi

        return {
            "base_icms": self._to_decimal(base_icms),
            "base_st": self._to_decimal(base_st),
        }

    # -----------------------------
    # ST
    # -----------------------------
    def calcular_st(self, base_st, icms_proprio, mva, aliq_icms):
        if not base_st or not mva or not aliq_icms:
            return None

        base_mva = base_st * (1 + mva / Decimal("100"))
        icms_total = self.calcular_valor(base_mva, aliq_icms)
        return self._to_decimal(icms_total - (icms_proprio or Decimal("0")))

    # -----------------------------
    # MÉTODO PRINCIPAL
    # -----------------------------
    def calcular_item(self, item, produto, uf_destino, pedi_tipo_oper):

        cfop = self.resolver_cfop(pedi_tipo_oper, uf_destino)
        ncm = self.obter_ncm(produto)

        aliquotas = self.obter_aliquotas_base(ncm)
        icms_data = self.obter_aliquotas_icms(uf_destino)
        aliquotas, icms_data = self.aplicar_overrides_ncm_cfop(ncm, cfop, aliquotas, icms_data)

        base_raiz = self.calcular_base_raiz(item)

        # IPI sempre primeiro
        valor_ipi = (
            self.calcular_valor(base_raiz, aliquotas["ipi"])
            if cfop.cfop_exig_ipi else None
        )

        bases = self.calcular_bases_icms_st(base_raiz, valor_ipi, cfop)

        valor_icms = (
            self.calcular_valor(bases["base_icms"], icms_data["icms"])
            if cfop.cfop_exig_icms else None
        )

        valor_st = (
            self.calcular_st(
                bases["base_st"],
                valor_icms,
                icms_data["mva_st"],
                icms_data["icms"],
            )
            if cfop.cfop_gera_st else None
        )

        return {
            "cfop": cfop,
            "bases": {
                "raiz": base_raiz,
                "icms": bases["base_icms"],
                "st": bases["base_st"],
                "pis": base_raiz,
                "cofins": base_raiz,
            },
            "valores": {
                "ipi": valor_ipi,
                "icms": valor_icms,
                "st": valor_st,
                "pis": self.calcular_valor(base_raiz, aliquotas["pis"]),
                "cofins": self.calcular_valor(base_raiz, aliquotas["cofins"]),
                "cbs": self.calcular_valor(base_raiz, aliquotas["cbs"]),
                "ibs": self.calcular_valor(base_raiz, aliquotas["ibs"]),
            },
            "aliquotas": aliquotas | icms_data,
        }

    def aplicar_no_item(self, item, pacote):
        """
        Preenche TODOS os campos fiscais do Itenspedidovenda
        usando o pacote fiscal calculado.
        """

        # Base
        item.iped_base_icms = bases["base_icms"]

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
        item.iped_base_pis = bases["base_pis"]
        item.iped_base_cofi = bases["base_cofins"]

        # Já deixa CST genérico (pode evoluir depois)
        if pacote["aliquotas"]["icms"]:
            item.iped_cst_icms = "000"
        if pacote["aliquotas"]["pis"]:
            item.iped_cst_pis = "01"
        if pacote["aliquotas"]["cofins"]:
            item.iped_cst_cofi = "01"

        return item
