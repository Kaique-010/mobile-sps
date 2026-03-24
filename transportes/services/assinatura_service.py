import logging
import hashlib
import base64
from lxml import etree
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding

from transportes.models import Cte
from Licencas.models import Filiais
from Notas_Fiscais.infrastructure.certificado_loader import CertificadoLoader

logger = logging.getLogger(__name__)

CTE_NS = "http://www.portalfiscal.inf.br/cte"
DSIG_NS = "http://www.w3.org/2000/09/xmldsig#"
C14N_ALG = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
ENVELOPED_ALG = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
RSA_SHA1_ALG = "http://www.w3.org/2000/09/xmldsig#rsa-sha1"
SHA1_ALG = "http://www.w3.org/2000/09/xmldsig#sha1"


class AssinaturaService:
    def __init__(self, cte: Cte):
        self.cte = cte
        self.filial = None
        self._carregar_filial()

    def _carregar_filial(self):
        try:
            db_alias = self.cte._state.db or 'default'
            self.filial = Filiais.objects.using(db_alias).defer('empr_cert_digi').filter(
                empr_empr=self.cte.empresa,
                empr_codi=self.cte.filial
            ).first()
            if not self.filial:
                raise Exception("Filial não encontrada.")
        except Exception as e:
            logger.error(f"Erro ao carregar dados da filial para assinatura: {e}")
            raise Exception("Dados da filial emitente não encontrados.")

    def _normalizar_xml(self, xml_str: str) -> str:
        xml = (xml_str or "").strip()
        xml = xml.lstrip("\ufeff\r\n\t ")
        if (xml.startswith('"') and xml.endswith('"')) or (xml.startswith("'") and xml.endswith("'")):
            xml = xml[1:-1].strip()
        while xml[:9].lower() == "undefined":
            xml = xml[9:].lstrip()
        while xml[-9:].lower() == "undefined":
            xml = xml[:-9].rstrip()
        if xml.startswith("<?xml"):
            idx = xml.find("?>")
            if idx != -1:
                xml = xml[idx + 2:].strip()
        return xml.strip()

    def _c14n_elemento(self, element, ns_uri: str) -> bytes:
        """
        Canonicalização C14N inclusiva (REC-xml-c14n-20010315) correta para SEFAZ.

        Problema: ao canonicalizar um elemento filho (ex: <infCte>) isoladamente,
        o lxml c14n inclusivo adiciona xmlns="" em todos os filhos porque o namespace
        default do pai (CTe) não está no nsmap do elemento isolado.

        Solução: garantir que o xmlns esteja no próprio elemento antes do c14n,
        injetando-o na serialização e relendo com lxml.
        """
        xml_str = etree.tostring(element, encoding="unicode")

        # Injeta o xmlns no elemento raiz se não estiver presente
        if f'xmlns="{ns_uri}"' not in xml_str and f"xmlns='{ns_uri}'" not in xml_str:
            primeiro = min(
                (xml_str.index(c) for c in [" ", ">", "/"] if c in xml_str),
                default=len(xml_str)
            )
            xml_str = xml_str[:primeiro] + f' xmlns="{ns_uri}"' + xml_str[primeiro:]

        el = etree.fromstring(xml_str.encode("utf-8"))
        return etree.tostring(el, method="c14n", exclusive=False, with_comments=False)

    def _sha1_b64(self, data: bytes) -> str:
        return base64.b64encode(hashlib.sha1(data).digest()).decode()

    def _rsa_sha1_sign(self, data: bytes, private_key) -> str:
        signature = private_key.sign(data, padding.PKCS1v15(), hashes.SHA1())
        return base64.b64encode(signature).decode()

    def _cert_der_b64(self, cert) -> str:
        """Certificado em base64 DER, sem cabeçalhos PEM, em linhas de 76 chars."""
        der = cert.public_bytes(Encoding.DER)
        b64 = base64.b64encode(der).decode()
        return "\n".join(b64[i:i+76] for i in range(0, len(b64), 76))

    def assinar(self, xml_content: str) -> str:
        """
        Assina o XML do CTe seguindo EXATAMENTE o padrao do MOC CTe v4.00:

        - CanonicalizationMethod : http://www.w3.org/TR/2001/REC-xml-c14n-20010315
        - SignatureMethod        : http://www.w3.org/2000/09/xmldsig#rsa-sha1
        - Transform[0]          : http://www.w3.org/2000/09/xmldsig#enveloped-signature
        - Transform[1]          : http://www.w3.org/TR/2001/REC-xml-c14n-20010315
        - DigestMethod          : http://www.w3.org/2000/09/xmldsig#sha1
        - Referencia            : atributo Id do <infCte> (URI="#CTe...")
        - Posicao do Signature  : ultimo filho do <CTe>
        """
        try:
            caminho_certificado, senha_certificado = CertificadoLoader(self.filial).load()
        except Exception as e:
            raise Exception(f"Certificado digital nao configurado/indisponivel: {str(e)}")

        if not caminho_certificado:
            raise Exception("Certificado digital nao configurado/indisponivel.")

        try:
            with open(caminho_certificado, "rb") as f:
                pfx_bytes = f.read()

            password = (senha_certificado or "").encode("utf-8") if senha_certificado else None
            private_key, cert, _chain = pkcs12.load_key_and_certificates(pfx_bytes, password)

            if private_key is None or cert is None:
                raise Exception("Certificado A1 invalido ou incompleto.")

            xml_content = self._normalizar_xml(xml_content)
            parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False)
            root = etree.fromstring(xml_content.encode("utf-8"), parser=parser)

            if etree.QName(root).localname != "CTe" or etree.QName(root).namespace != CTE_NS:
                raise Exception("XML invalido: raiz deve ser <CTe> no namespace do CT-e.")

            ns = {"cte": CTE_NS}
            inf_list = root.xpath("//cte:infCte", namespaces=ns)
            if not inf_list:
                raise Exception("Elemento infCte nao encontrado para assinatura.")

            inf = inf_list[0]
            inf_id = (inf.get("Id") or "").strip()
            if not inf_id:
                raise Exception("infCte sem atributo Id.")

            # Homologação: força xNome do remetente
            try:
                tp_amb_el = root.find(".//{*}tpAmb")
                tp_amb_val = (tp_amb_el.text or "").strip() if tp_amb_el is not None else ""
                if tp_amb_val == "2":
                    esperado = "CTE EMITIDO EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
                    rem_xnome_el = root.find(".//{*}rem/{*}xNome")
                    if rem_xnome_el is not None:
                        rem_xnome_el.text = esperado
                    dest_xnome_el = root.find(".//{*}dest/{*}xNome")
                    if dest_xnome_el is not None:
                        dest_xnome_el.text = esperado
                    exped_xnome_el = root.find(".//{*}exped/{*}xNome")
                    if exped_xnome_el is not None:
                        exped_xnome_el.text = esperado
                    receb_xnome_el = root.find(".//{*}receb/{*}xNome")
                    if receb_xnome_el is not None:
                        receb_xnome_el.text = esperado
                    toma4_xnome_el = root.find(".//{*}toma4/{*}xNome")
                    if toma4_xnome_el is not None:
                        toma4_xnome_el.text = esperado
            except Exception:
                pass

            # -----------------------------------------------------------
            # 1. C14N do <infCte> e DigestValue (SHA-1)
            #    CRITICO: usar _c14n_elemento para evitar xmlns="" nos filhos
            # -----------------------------------------------------------
            inf_c14n = self._c14n_elemento(inf, CTE_NS)
            logger.debug(f"C14N infCte (primeiros 300): {inf_c14n[:300]}")
            digest_value = self._sha1_b64(inf_c14n)

            # -----------------------------------------------------------
            # 2. Monta <SignedInfo> com namespace explicito
            # -----------------------------------------------------------
            signed_info_xml = (
                f'<SignedInfo xmlns="{DSIG_NS}">'
                f'<CanonicalizationMethod Algorithm="{C14N_ALG}"></CanonicalizationMethod>'
                f'<SignatureMethod Algorithm="{RSA_SHA1_ALG}"></SignatureMethod>'
                f'<Reference URI="#{inf_id}">'
                f'<Transforms>'
                f'<Transform Algorithm="{ENVELOPED_ALG}"></Transform>'
                f'<Transform Algorithm="{C14N_ALG}"></Transform>'
                f'</Transforms>'
                f'<DigestMethod Algorithm="{SHA1_ALG}"></DigestMethod>'
                f'<DigestValue>{digest_value}</DigestValue>'
                f'</Reference>'
                f'</SignedInfo>'
            )

            # -----------------------------------------------------------
            # 3. C14N do <SignedInfo> e assinatura RSA-SHA1
            # -----------------------------------------------------------
            signed_info_el = etree.fromstring(signed_info_xml.encode("utf-8"))
            signed_info_c14n = self._c14n_elemento(signed_info_el, DSIG_NS)
            logger.debug(f"C14N SignedInfo (primeiros 200): {signed_info_c14n[:200]}")
            signature_value = self._rsa_sha1_sign(signed_info_c14n, private_key)

            # -----------------------------------------------------------
            # 4. Monta <Signature> completo e anexa ao <CTe>
            # -----------------------------------------------------------
            cert_b64 = self._cert_der_b64(cert)

            signature_xml = (
                f'<Signature xmlns="{DSIG_NS}">'
                f'{signed_info_xml}'
                f'<SignatureValue>{signature_value}</SignatureValue>'
                f'<KeyInfo>'
                f'<X509Data>'
                f'<X509Certificate>{cert_b64}</X509Certificate>'
                f'</X509Data>'
                f'</KeyInfo>'
                f'</Signature>'
            )

            sig_el = etree.fromstring(signature_xml.encode("utf-8"))
            root.append(sig_el)

            result = etree.tostring(
                root,
                encoding="utf-8",
                pretty_print=False,
                xml_declaration=False,
            ).decode("utf-8")

            logger.debug(f"XML assinado com sucesso. Id={inf_id}, DigestValue={digest_value}")
            return result

        except Exception as e:
            logger.error(f"Erro ao assinar XML: {e}")
            raise Exception(f"Falha na assinatura digital: {str(e)}")
