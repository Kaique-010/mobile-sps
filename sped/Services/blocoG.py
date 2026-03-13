from calendar import monthrange


def _fmt_data(d):
    if not d:
        return ""
    return d.strftime("%d%m%Y")


def _periodo_mensal(data_inicio, data_fim):
    ini = data_inicio
    fim = data_fim
    if not ini or not fim:
        return ini, fim
    fim_mes = monthrange(fim.year, fim.month)[1]
    ini_mes = ini.replace(day=1)
    fim_mes = fim.replace(day=fim_mes)
    return ini_mes, fim_mes


class BlocoGService:
    def __init__(self, *, data_inicio, data_fim):
        self.data_inicio = data_inicio
        self.data_fim = data_fim

    def gerar(self):
        dt_ini, dt_fim = _periodo_mensal(self.data_inicio, self.data_fim)
        linhas = ["|G001|1|"]
        if dt_ini and dt_fim:
            linhas.append("|G990|{qtd}|".format(qtd=len(linhas) + 1))
        else:
            linhas.append("|G990|{qtd}|".format(qtd=len(linhas) + 1))
        return linhas
