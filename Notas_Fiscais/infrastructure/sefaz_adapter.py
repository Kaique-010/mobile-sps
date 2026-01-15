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
        
        status = None
        motivo = None
        protocolo = None
        chave = None
        xml_protocolo = None

        try:
            # envio[0] é o status retornado pelo PyNFe (pode ser 1 para sucesso, mas precisamos do cStat da SEFAZ)
            # envio[1] é o objeto response do requests
            resposta = envio[1]
            
            # Tenta extrair informações do XML de retorno da SEFAZ
            if resposta and hasattr(resposta, 'content'):
                try:
                    from lxml import etree
                    root = etree.fromstring(resposta.content)
                    ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
                    
                    # Procura por protNFe (Protocolo de Autorização)
                    prot_nfe = root.find('.//ns:protNFe', namespaces=ns)
                    if prot_nfe is not None:
                        # Extrai o XML do protocolo para montar o procNFe posteriormente
                        xml_protocolo = etree.tostring(prot_nfe, encoding='unicode')

                        inf_prot = prot_nfe.find('.//ns:infProt', namespaces=ns)
                        if inf_prot is not None:
                            # cStat
                            c_stat_elem = inf_prot.find('.//ns:cStat', namespaces=ns)
                            if c_stat_elem is not None:
                                status = int(c_stat_elem.text)
                            
                            # nProt
                            n_prot_elem = inf_prot.find('.//ns:nProt', namespaces=ns)
                            if n_prot_elem is not None:
                                protocolo = n_prot_elem.text
                                
                            # xMotivo
                            x_motivo_elem = inf_prot.find('.//ns:xMotivo', namespaces=ns)
                            if x_motivo_elem is not None:
                                motivo = x_motivo_elem.text
                            
                            # chNFe
                            ch_nfe_elem = inf_prot.find('.//ns:chNFe', namespaces=ns)
                            if ch_nfe_elem is not None:
                                chave = ch_nfe_elem.text

                    # Se não achou protNFe, pode ser rejeição no nível do lote ou processamento
                    if status is None:
                        c_stat_elem = root.find('.//ns:cStat', namespaces=ns)
                        if c_stat_elem is not None:
                            status = int(c_stat_elem.text)
                        
                        x_motivo_elem = root.find('.//ns:xMotivo', namespaces=ns)
                        if x_motivo_elem is not None:
                            motivo = x_motivo_elem.text

                except Exception as e_parse:
                    # Fallback se falhar o parser XML
                    motivo = f"Erro ao parsear XML SEFAZ: {str(e_parse)}"
            
            # Fallback se status ainda for None, usa o do PyNFe ou assume erro
            if status is None:
                status = envio[0]
                motivo = getattr(resposta, 'text', str(resposta))

        except Exception as e:
            motivo = str(e)
            status = None

        return {
            "xml": xml_assinado,
            "codigo": None,
            "motivo": motivo,
            "status": status,
            "protocolo": protocolo,
            "chave": chave,
            "xml_protocolo": xml_protocolo,
        }
