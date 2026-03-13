from collections import Counter


def _reg(linha):
    if not linha:
        return ""
    if linha[0] != "|":
        return ""
    partes = linha.split("|")
    if len(partes) < 2:
        return ""
    return partes[1].strip()


class Bloco9Service:
    def __init__(self, *, linhas_anteriores):
        self.linhas_anteriores = [l for l in (linhas_anteriores or []) if l]

    def gerar(self):
        counts = Counter()
        for l in self.linhas_anteriores:
            r = _reg(l)
            if r:
                counts[r] += 1

        regs = set(counts.keys())
        regs.update({"9001", "9900", "9990", "9999"})
        regs_ordenados = sorted(regs)

        qtd_9900 = len(regs_ordenados)
        counts["9001"] = 1
        counts["9900"] = qtd_9900
        counts["9990"] = 1
        counts["9999"] = 1

        bloco9 = ["|9001|0|"]
        for r in regs_ordenados:
            bloco9.append("|9900|{reg}|{qtd}|".format(reg=r, qtd=counts.get(r, 0)))

        bloco9.append("|9990|{qtd}|".format(qtd=len(bloco9) + 2))

        total_arquivo = len(self.linhas_anteriores) + len(bloco9) + 1
        bloco9.append("|9999|{qtd}|".format(qtd=total_arquivo))
        return bloco9
