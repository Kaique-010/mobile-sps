from calendar import monthrange
from decimal import Decimal
from django.db.utils import OperationalError, ProgrammingError
from sped.models import SaldoProduto


def _fmt_data(d):
    if not d:
        return ""
    return d.strftime("%d%m%Y")


def _fmt_decimal(v, casas=2):
    if v is None:
        return ""
    try:
        q = Decimal(v).quantize(Decimal("1." + ("0" * int(casas))))
    except Exception:
        q = Decimal("0").quantize(Decimal("1." + ("0" * int(casas))))
    s = format(q, "f")
    return s.replace(".", ",")


def _periodo_mensal(data_inicio, data_fim):
    ini = data_inicio
    fim = data_fim
    if not ini or not fim:
        return ini, fim
    fim_mes = monthrange(fim.year, fim.month)[1]
    ini_mes = ini.replace(day=1)
    fim_mes = fim.replace(day=fim_mes)
    return ini_mes, fim_mes


class BlocoKService:
    def __init__(self, *, db_alias, empresa_id, filial_id, data_inicio, data_fim):
        self.db_alias = db_alias
        self.empresa_id = int(empresa_id)
        self.filial_id = int(filial_id)
        self.data_inicio = data_inicio
        self.data_fim = data_fim

    def gerar(self):
        dt_ini, dt_fim = _periodo_mensal(self.data_inicio, self.data_fim)

        try:
            saldos = list(
                SaldoProduto.objects.using(self.db_alias)
                .filter(empresa=str(self.empresa_id), filial=str(self.filial_id), saldo_estoque__gt=0)
                .order_by("produto_codigo_id")
            )
        except (ProgrammingError, OperationalError):
            saldos = []

        if not saldos:
            return ["|K001|1|", "|K990|2|"]

        linhas = ["|K001|0|"]
        linhas.append("|K100|{ini}|{fim}|".format(ini=_fmt_data(dt_ini), fim=_fmt_data(dt_fim)))

        dt_est = _fmt_data(dt_fim)
        for s in saldos:
            cod_item = (s.produto_codigo_id or "").strip()
            qtd = Decimal(s.saldo_estoque or 0)
            if qtd <= 0:
                continue
            linhas.append("|K200|{dt_est}|{cod_item}|{qtd}|0|||||".format(dt_est=dt_est, cod_item=cod_item, qtd=_fmt_decimal(qtd, 3)))

        linhas.append("|K990|{qtd}|".format(qtd=len(linhas) + 1))
        return linhas
