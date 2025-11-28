from pynfe.processamento.comunicacao import ComunicacaoSefaz
from pynfe.processamento.assinatura import AssinaturaA1
from pynfe.processamento.serializacao import SerializacaoXML
from pynfe.entidades.fonte_dados import _fonte_dados

class SefazAdapter:

    def __init__(self, cert_path, cert_pass, uf, ambiente):
        self.uf = uf
        self.ambiente = ambiente
        self.cert_path = cert_path
        self.cert_pass = cert_pass
        self.assinador = AssinaturaA1(cert_path, cert_pass)
        self.homologacao = True if int(ambiente) == 2 else False
        self.comunicacao = ComunicacaoSefaz(uf, cert_path, cert_pass, self.homologacao)

    def emitir(self, nota_fiscal):
        serializador = SerializacaoXML(_fonte_dados, homologacao=self.homologacao)
        nfe = serializador.exportar(nota_fiscal)
        xml_assinado = self.assinador.assinar(nfe)

        envio = self.comunicacao.autorizacao(modelo='nfe', nota_fiscal=xml_assinado)
        try:
            status = envio[0]
            resposta = envio[1]
            chave = None
            protocolo = None
        except Exception:
            status = None
            resposta = None
            chave = None
            protocolo = None

        return {
            "xml": xml_assinado,
            "codigo": None,
            "motivo": getattr(resposta, 'text', None) if resposta is not None else None,
            "status": status,
            "protocolo": protocolo,
            "chave": chave,
        }
