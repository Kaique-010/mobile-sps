from calendar import monthrange
from decimal import Decimal


def _fmt_data(d):
    if not d:
        return ""
    return d.strftime("%d%m%Y")


def _fmt_decimal(v, casas=2):
    if v is None:
        v = Decimal("0")
    try:
        q = Decimal(v).quantize(Decimal("1." + ("0" * int(casas))))
    except Exception:
        q = Decimal("0").quantize(Decimal("1." + ("0" * int(casas))))
    s = format(q, "f")
    return s.replace(".", ",")


def _to_decimal_br(v):
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    s = str(v).strip()
    if not s:
        return Decimal("0")
    try:
        return Decimal(s.replace(".", "").replace(",", "."))
    except Exception:
        return Decimal("0")


def _periodo_mensal(data_inicio, data_fim):
    ini = data_inicio
    fim = data_fim
    if not ini or not fim:
        return ini, fim
    fim_mes = monthrange(fim.year, fim.month)[1]
    ini_mes = ini.replace(day=1)
    fim_mes = fim.replace(day=fim_mes)
    return ini_mes, fim_mes


class BlocoEService:
    def __init__(self, *, data_inicio, data_fim, linhas_blococ, cod_receita=None, data_vencimento=None):
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        self.linhas_blococ = list(linhas_blococ or [])
        self.cod_receita = (cod_receita or "").strip()
        self.data_vencimento = data_vencimento

    def _somar_icms_c190(self):
        total = Decimal("0")
        for l in self.linhas_blococ:
            if not l or not l.startswith("|C190|"):
                continue
            partes = l.split("|")
            if len(partes) < 7:
                continue
            total += _to_decimal_br(partes[6])
        return total

    def gerar(self):
        dt_ini, dt_fim = _periodo_mensal(self.data_inicio, self.data_fim)

        linhas = ["|E001|0|"]
        linhas.append("|E100|{ini}|{fim}|".format(ini=_fmt_data(dt_ini), fim=_fmt_data(dt_fim)))

        vl_tot_debitos = self._somar_icms_c190()
        vl_tot_creditos = Decimal("0")
        vl_sld_apurado = (vl_tot_debitos - vl_tot_creditos)
        vl_icms_recolher = vl_sld_apurado if vl_sld_apurado > 0 else Decimal("0")
        vl_sld_credor_transportar = (-vl_sld_apurado) if vl_sld_apurado < 0 else Decimal("0")

        linhas.append(
            "|E110|{vl_tot_debitos}|0,00|0,00|0,00|{vl_tot_creditos}|0,00|0,00|0,00|0,00|{vl_sld_apurado}|0,00|{vl_icms_recolher}|{vl_sld_credor_transportar}|0,00|".format(
                vl_tot_debitos=_fmt_decimal(vl_tot_debitos, 2),
                vl_tot_creditos=_fmt_decimal(vl_tot_creditos, 2),
                vl_sld_apurado=_fmt_decimal(vl_sld_apurado, 2),
                vl_icms_recolher=_fmt_decimal(vl_icms_recolher, 2),
                vl_sld_credor_transportar=_fmt_decimal(vl_sld_credor_transportar, 2),
            )
        )

        if vl_icms_recolher > 0 and self.cod_receita and self.data_vencimento:
            linhas.append(
                "|E116|000|{vl}|{dt_vcto}|{cod_rec}||||||".format(
                    vl=_fmt_decimal(vl_icms_recolher, 2),
                    dt_vcto=_fmt_data(self.data_vencimento),
                    cod_rec=self.cod_receita,
                )
            )

        linhas.append("|E990|{qtd}|".format(qtd=len(linhas) + 1))
        return linhas
