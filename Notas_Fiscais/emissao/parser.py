from lxml import etree

class SefazResponseParser:

    def parse(self, xml):
        tree = etree.fromstring(xml.encode("utf-8"))

        # extrai valores essenciais
        cStat = tree.xpath("//cStat/text()")
        xMotivo = tree.xpath("//xMotivo/text()")
        prot = tree.xpath("//protNFe/text()")
        chave = tree.xpath("//chNFe/text()")

        return {
            "status": cStat[0] if cStat else None,
            "motivo": xMotivo[0] if xMotivo else None,
            "protocolo": prot[0] if prot else None,
            "chave": chave[0] if chave else None,
            "raw": xml
        }
