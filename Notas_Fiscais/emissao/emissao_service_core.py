import tempfile
import os
from .assinatura import AssinadorA1Service
from .sefaz_client import SefazClient
from .parser import SefazResponseParser
from .gerador_xml import GeradorXML
from .urls_sefaz import URLS_SEFAZ
from .exceptions import ErroEmissao


class EmissaoServiceCore:

    def __init__(self, dto_dict, filial):
        self.dto = dto_dict
        self.filial = filial

        # ambiente NFe (1=Produção, 2=Homologação)
        self.ambiente = int(filial.empr_ambi_nfe or 2)

    # ----------------------------------------------------------
    # Fluxo completo: gerar XML → assinar → enviar → parsear
    # ----------------------------------------------------------
    def emitir(self):
        try:
            # 1. gerar xml cru (sem assinatura)
            xml_gerado = GeradorXML().gerar(self.dto)

            # 2. carregar certificado
            pfx_path, pfx_pass = self._load_certificado()

            # 3. assinar XML
            assinador = AssinadorA1Service(pfx_path, pfx_pass)
            xml_assinado = assinador.assinar_xml(xml_gerado)

            # 4. URL SEFAZ
            url = self._resolve_url()

            # 5. extrair cert.pem e key.pem
            cert_pem, key_pem = assinador._extract_keys()

            # 6. Enviar SOAP
            resposta_xml = SefazClient(cert_pem, key_pem, url, verify=self._resolve_verify()).enviar_xml(xml_assinado)

            # 7. Parsear resposta
            return SefazResponseParser().parse(resposta_xml), xml_assinado, resposta_xml

        except Exception as e:
            raise ErroEmissao(str(e))

    # ----------------------------------------------------------
    def _load_certificado(self):
        if not self.filial.empr_cert_digi:
            raise ErroEmissao("Filial não possui certificado digital cadastrado.")

        arq = tempfile.NamedTemporaryFile(delete=False, suffix=".pfx")
        arq.write(self.filial.empr_cert_digi)
        arq.flush()

        return arq.name, self.filial.empr_senh_cert

    # ----------------------------------------------------------
    def _resolve_url(self):
        uf = self.filial.empr_esta or "PR"
        try:
            return URLS_SEFAZ[uf]["autorizacao_producao" if self.ambiente == 1 else "autorizacao_homologacao"]
        except:
            raise ErroEmissao(f"Webservice SEFAZ não configurado para UF={uf}")

    # ----------------------------------------------------------
    def _resolve_verify(self):
        # 1) CA bundle via env
        bundle = os.getenv("SEFAZ_CA_BUNDLE")
        if bundle:
            try:
                p = os.path.expanduser(bundle)
                p = os.path.normpath(p)
                if os.path.isfile(p):
                    return p
            except Exception:
                pass

        # 2) Por filial: se houver indicação explícita de desabilitar (não recomendado)
        # Mantemos verificação ativa por padrão
        try:
            flag = getattr(self.filial, "empr_cone_segu", True)
            if flag is False:
                return True  # ainda preferimos manter verificação ativa
        except Exception:
            pass

        return True
