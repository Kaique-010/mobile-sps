from decimal import Decimal
from django.db.models import Sum
from django.db.utils import OperationalError, ProgrammingError
from sped.models import Infvv, Nfevv, NotaFiscal, NotaFiscalItem, NotaFiscalItemImposto, NotaFiscalTransporte, Produtos


def _fmt_data(d):
    if not d:
        return ""
    return d.strftime("%d%m%Y")


def _fmt_decimal(v, casas=2):
    if v is None:
        return "0," + ("0" * int(casas))
    try:
        q = Decimal(v).quantize(Decimal("1." + ("0" * int(casas))))
    except Exception:
        q = Decimal("0").quantize(Decimal("1." + ("0" * int(casas))))
    s = format(q, "f")
    return s.replace(".", ",")


def _cod_sit(status):
    if status == 101: return "02"
    if status == 102: return "04"
    if status in (301, 302): return "05"
    return "00"


def _cod_sit_nfevv(n):
    if getattr(n, "cancelada", False) or getattr(n, "status_nfe", None) == 101:
        return "02"
    if getattr(n, "inutilizada", False):
        return "04"
    if getattr(n, "denegada", False):
        return "05"
    return "00"


class BlocoCService:
    def __init__(self, *, db_alias, empresa_id, filial_id, data_inicio, data_fim):
        self.db_alias = db_alias
        self.empresa_id = int(empresa_id)
        self.filial_id = int(filial_id)
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        self.contadores = {}

    def _registrar(self, registro, linha):
        self.contadores[registro] = self.contadores.get(registro, 0) + 1
        return linha

    def _usar_nfevv(self):
        try:
            if (NotaFiscal.objects.using(self.db_alias).filter(
                empresa=self.empresa_id, filial=self.filial_id,
                data_emissao__range=(self.data_inicio, self.data_fim),
            ).exclude(status=0).exists()):
                return False
        except (ProgrammingError, OperationalError):
            pass
        try:
            return (Nfevv.objects.using(self.db_alias).filter(
                empresa=self.empresa_id, filial=self.filial_id,
                b09_demi__range=(self.data_inicio, self.data_fim),
                status_nfe=100,
            ).exists())
        except (ProgrammingError, OperationalError):
            return False

    def gerar(self):
        linhas = [self._registrar("C001", "|C001|0|")]
        usar_nfevv = self._usar_nfevv()

        if usar_nfevv:
            notas = (Nfevv.objects.using(self.db_alias).filter(
                empresa=self.empresa_id, filial=self.filial_id,
                b09_demi__range=(self.data_inicio, self.data_fim),
                status_nfe=100,
            ).order_by("b09_demi", "b06_mod", "b07_serie", "b08_nnf"))

            # Cache de produtos (Evita N+1 queries)
            nota_ids = notas.values_list("id", flat=True)
            prod_ids = (
                Infvv.objects.using(self.db_alias)
                .filter(id__in=nota_ids)
                .exclude(i02_cprod__isnull=True)
                .exclude(i02_cprod="")
                .values_list("i02_cprod", flat=True)
                .distinct()
            )
            prod_map = {
                p.prod_codi: p.prod_unme_id
                for p in Produtos.objects.using(self.db_alias)
                .filter(prod_empr=str(self.empresa_id), prod_codi__in=prod_ids)
                .only("prod_codi", "prod_unme")
            }

            for nota in notas.iterator():
                resumo_c190 = {}
                itens = list(Infvv.objects.using(self.db_alias).filter(id=nota.id).order_by("nitem").values(
                    "nitem", "i02_cprod", "i09_ucom", "i10_qcom", "i11_vprod", "i17_vdesc",
                    "i08_cfop", "n12_cst", "n15_vbc", "n16_picms", "n17_vicms", "n21_vbcst", 
                    "n23_vicmsst", "o14_vipi", "q06_cst_pis", "q09_vpis", "s06_cst_cofins", "s11_vcofins"
                ))

                doc = "".join(filter(str.isdigit, str(getattr(nota, "e02_cnpj", "") or getattr(nota, "e03_cpf", ""))))
                cod_part = doc or f"NFE{nota.b06_mod}{nota.b07_serie}{nota.b08_nnf}"
                
                linhas.append(self._registrar("C100", "|C100|1|0|{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}|1|{8}|0,00|{9}|{10}|{11}|{12}|{13}|{14}|{15}|{16}|{17}|{18}|{19}|{20}|||".format(
                    cod_part, nota.b06_mod or "55", _cod_sit_nfevv(nota), nota.b07_serie or "", nota.b08_nnf or "", 
                    (nota.a03_id or "").strip(), _fmt_data(nota.b09_demi), _fmt_data(nota.b10_dsaient or nota.b09_demi),
                    _fmt_decimal(nota.w16_vnf_tota), _fmt_decimal(nota.w10_vdesc_tota), _fmt_decimal(nota.w07_vprod_tota),
                    getattr(nota, "x02_modfrete", 9), _fmt_decimal(nota.w08_vfret_tota), _fmt_decimal(nota.w09_vseg_tota),
                    _fmt_decimal(nota.w15_voutro_tota), _fmt_decimal(nota.w03_vbc_tota), _fmt_decimal(nota.w04_vicms_tota),
                    _fmt_decimal(nota.w05_vbcst_tota), _fmt_decimal(nota.w06_vst_tota), _fmt_decimal(nota.w12_vipi_tota),
                    _fmt_decimal(nota.w13_vpis_tota), _fmt_decimal(nota.w14_vcofins_tota)
                )))

                for it in itens:
                    unid = (prod_map.get(it["i02_cprod"]) or "") or it.get("i09_ucom") or ""
                    linhas.append(self._registrar("C170", "|C170|{0}|{1}||{2}|{3}|{4}|{5}|0|{6}|{7}||{8}|{9}|{10}|{11}||{12}|||||{13}|{14}|{15}|||{16}|{17}|{18}|||{19}|".format(
                        it["nitem"], it["i02_cprod"], _fmt_decimal(it["i10_qcom"], 4), unid, _fmt_decimal(it["i11_vprod"]),
                        _fmt_decimal(it["i17_vdesc"]), it["n12_cst"], it["i08_cfop"], _fmt_decimal(it["n15_vbc"]),
                        _fmt_decimal(it["n16_picms"]), _fmt_decimal(it["n17_vicms"]), _fmt_decimal(it["n21_vbcst"]),
                        _fmt_decimal(it["n23_vicmsst"]), _fmt_decimal(it["o14_vipi"]), it["q06_cst_pis"],
                        _fmt_decimal(it["q09_vpis"]), it["s06_cst_cofins"], _fmt_decimal(it["s11_vcofins"]), "", ""
                    )))

                    # Lógica de Agrupamento C190 para Nfevv
                    chave = (str(it["n12_cst"]).strip(), str(it["i08_cfop"]).strip(), Decimal(it["n16_picms"] or 0))
                    if chave not in resumo_c190:
                        resumo_c190[chave] = {'vl_opr': Decimal(0), 'vl_bc': Decimal(0), 'vl_icms': Decimal(0), 'vl_bc_st': Decimal(0), 'vl_st': Decimal(0), 'vl_ipi': Decimal(0)}
                    resumo_c190[chave]['vl_opr'] += Decimal(it["i11_vprod"] or 0)
                    resumo_c190[chave]['vl_bc'] += Decimal(it["n15_vbc"] or 0)
                    resumo_c190[chave]['vl_icms'] += Decimal(it["n17_vicms"] or 0)
                    resumo_c190[chave]['vl_bc_st'] += Decimal(it["n21_vbcst"] or 0)
                    resumo_c190[chave]['vl_st'] += Decimal(it["n23_vicmsst"] or 0)
                    resumo_c190[chave]['vl_ipi'] += Decimal(it["o14_vipi"] or 0)

                for c, v in resumo_c190.items():
                    linhas.append(self._registrar("C190", "|C190|{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}|0,00|{8}||".format(
                        c[0], c[1], _fmt_decimal(c[2]), _fmt_decimal(v['vl_opr']), _fmt_decimal(v['vl_bc']),
                        _fmt_decimal(v['vl_icms']), _fmt_decimal(v['vl_bc_st']), _fmt_decimal(v['vl_st']), _fmt_decimal(v['vl_ipi'])
                    )))

        else:
            notas = (NotaFiscal.objects.using(self.db_alias).select_related("destinatario").filter(
                empresa=self.empresa_id, filial=self.filial_id,
                data_emissao__range=(self.data_inicio, self.data_fim),
            ).exclude(status=0).order_by("data_emissao", "modelo", "serie", "numero"))

            # Cache de produtos
            prod_ids = NotaFiscalItem.objects.using(self.db_alias).filter(nota__in=notas).values_list('produto_id', flat=True).distinct()
            prod_map = {
                p.prod_codi: p.prod_unme_id
                for p in Produtos.objects.using(self.db_alias)
                .filter(prod_empr=str(self.empresa_id), prod_codi__in=prod_ids)
                .only("prod_codi", "prod_unme")
            }

            for nota in notas.iterator():
                resumo_c190 = {}
                itens_qs = NotaFiscalItem.objects.using(self.db_alias).filter(nota_id=nota.id)
                itens_data = list(itens_qs.values("id", "produto_id", "quantidade", "total_item", "desconto", "cfop", "cst_icms"))
                
                # Agregação de impostos para a nota (C100)
                impostos = NotaFiscalItemImposto.objects.using(self.db_alias).filter(item__nota_id=nota.id).values(
                    "item_id", "icms_base", "icms_valor", "icms_aliquota", "icms_st_base", "icms_st_valor", "ipi_valor", "pis_valor", "cofins_valor"
                )
                imp_map = {i["item_id"]: i for i in impostos}

                # Cálculo de totais da nota
                tot = itens_qs.aggregate(m=Sum("total_item"), d=Sum("desconto"), f=Sum("valor_frete"), s=Sum("valor_seguro"), o=Sum("valor_outras_despesas"))
                vl_n = (Decimal(tot['m'] or 0) + Decimal(tot['f'] or 0) + Decimal(tot['s'] or 0) + Decimal(tot['o'] or 0)) - Decimal(tot['d'] or 0)

                doc = str(nota.destinatario.enti_clie) if nota.destinatario else ""
                linhas.append(self._registrar("C100", "|C100|1|0|{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}|1|{8}|0,00|{9}||{10}|||||||||||||".format(
                    doc, nota.modelo or "55", _cod_sit(nota.status), nota.serie or "", nota.numero, nota.chave_acesso or "",
                    _fmt_data(nota.data_emissao), _fmt_data(nota.data_saida or nota.data_emissao), _fmt_decimal(vl_n), _fmt_decimal(tot['d']), _fmt_decimal(tot['m'])
                )))

                for it in itens_data:
                    imp = imp_map.get(it["id"], {})
                    unid = prod_map.get(it["produto_id"]) or ""
                    linhas.append(self._registrar("C170", "|C170|{0}|{1}||{2}|{3}|{4}|{5}|0|{6}|{7}||{8}|{9}|{10}|{11}||{12}|||||{13}|||||||||||".format(
                        it["id"], it["produto_id"], _fmt_decimal(it["quantidade"], 4), unid, _fmt_decimal(it["total_item"]),
                        _fmt_decimal(it["desconto"]), it["cst_icms"], it["cfop"], _fmt_decimal(imp.get("icms_base")),
                        _fmt_decimal(imp.get("icms_aliquota")), _fmt_decimal(imp.get("icms_valor")), _fmt_decimal(imp.get("icms_st_base")), _fmt_decimal(imp.get("icms_st_valor")), _fmt_decimal(imp.get("ipi_valor"))
                    )))

                    # Agrupamento C190 para NotaFiscal
                    chave = (str(it["cst_icms"]).strip(), str(it["cfop"]).strip(), Decimal(imp.get("icms_aliquota") or 0))
                    if chave not in resumo_c190:
                        resumo_c190[chave] = {'vl_opr': Decimal(0), 'vl_bc': Decimal(0), 'vl_icms': Decimal(0), 'vl_bc_st': Decimal(0), 'vl_st': Decimal(0), 'vl_ipi': Decimal(0)}
                    resumo_c190[chave]['vl_opr'] += Decimal(it["total_item"] or 0)
                    resumo_c190[chave]['vl_bc'] += Decimal(imp.get("icms_base") or 0)
                    resumo_c190[chave]['vl_icms'] += Decimal(imp.get("icms_valor") or 0)
                    resumo_c190[chave]['vl_bc_st'] += Decimal(imp.get("icms_st_base") or 0)
                    resumo_c190[chave]['vl_st'] += Decimal(imp.get("icms_st_valor") or 0)
                    resumo_c190[chave]['vl_ipi'] += Decimal(imp.get("ipi_valor") or 0)

                for c, v in resumo_c190.items():
                    linhas.append(self._registrar("C190", "|C190|{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}|0,00|{8}||".format(
                        c[0], c[1], _fmt_decimal(c[2]), _fmt_decimal(v['vl_opr']), _fmt_decimal(v['vl_bc']),
                        _fmt_decimal(v['vl_icms']), _fmt_decimal(v['vl_bc_st']), _fmt_decimal(v['vl_st']), _fmt_decimal(v['vl_ipi'])
                    )))

        linhas.append(self._registrar("C990", "|C990|{0}|".format(len(linhas) + 1)))
        return linhas
