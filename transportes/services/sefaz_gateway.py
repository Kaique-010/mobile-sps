import logging
import os
import tempfile
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from lxml import etree
from cryptography.hazmat.primitives.serialization import (
    pkcs12,
    Encoding,
    PrivateFormat,
    NoEncryption,
)

from transportes.models import Cte
from Licencas.models import Filiais
from Notas_Fiscais.infrastructure.certificado_loader import CertificadoLoader

logger = logging.getLogger(__name__)

CTE_NS = "http://www.portalfiscal.inf.br/cte"
SOAP_ENV = "http://www.w3.org/2003/05/soap-envelope"
SOAP_ENV_11 = "http://schemas.xmlsoap.org/soap/envelope/"

URLS_SEFAZ_CTE = {
    "PR": {
        "producao": {
            "recepcao_sinc": "https://cte.fazenda.pr.gov.br/cte4/CTeRecepcaoSincV4",
            "consulta": "https://cte.fazenda.pr.gov.br/cte4/CTeConsultaV4",
        },
        "homologacao": {
            "recepcao_sinc": "https://homologacao.cte.fazenda.pr.gov.br/cte4/CTeRecepcaoSincV4",
            "consulta": "https://homologacao.cte.fazenda.pr.gov.br/cte4/CTeConsultaV4",
        },
    },
    "SP": {
        "producao": {
            "recepcao_sinc": "https://nfe.fazenda.sp.gov.br/CTeWS/WS/CTeRecepcaoSincV4.asmx",
            "consulta": "https://nfe.fazenda.sp.gov.br/CTeWS/WS/CTeConsultaV4.asmx",
        },
        "homologacao": {
            "recepcao_sinc": "https://homologacao.nfe.fazenda.sp.gov.br/CTeWS/WS/CTeRecepcaoSincV4.asmx",
            "consulta": "https://homologacao.nfe.fazenda.sp.gov.br/CTeWS/WS/CTeConsultaV4.asmx",
        },
    },
    "MS": {
        "producao": {
            "recepcao_sinc": "https://producao.cte.ms.gov.br/ws/CTeRecepcaoSincV4",
            "consulta": "https://producao.cte.ms.gov.br/ws/CTeConsultaV4",
        },
        "homologacao": {
            "recepcao_sinc": "https://homologacao.cte.ms.gov.br/ws/CTeRecepcaoSincV4",
            "consulta": "https://homologacao.cte.ms.gov.br/ws/CTeConsultaV4",
        },
    },
}


class SefazGateway:
    def __init__(self, cte: Cte):
        self.cte = cte
        self.filial = None
        self._carregar_filial()

    def _carregar_filial(self):
        try:
            db_alias = self.cte._state.db or "default"
            self.filial = (
                Filiais.objects.using(db_alias)
                .defer("empr_cert_digi")
                .filter(empr_empr=self.cte.empresa, empr_codi=self.cte.filial)
                .first()
            )
            if not self.filial:
                raise Exception("Filial não encontrada.")
        except Exception as e:
            logger.error(f"Erro ao carregar dados da filial para SEFAZ: {e}")
            raise Exception("Dados da filial emitente não encontrados.")

    # ------------------------------------------------------------------
    # ENVIO
    # ------------------------------------------------------------------

    def enviar(self, xml_assinado: str) -> dict:
        """Envia o XML assinado para a SEFAZ e processa o retorno."""
        ambiente = self._ambiente()
        cert_pem_path, key_pem_path = self._get_cert_pem_and_key_pem()
        uf = self._uf()

        url = self._get_url(uf=uf, ambiente=ambiente, servico="recepcao_sinc")
        wsdl_ns = "http://www.portalfiscal.inf.br/cte/wsdl/CTeRecepcaoSincV4"

        cuf = self._cuf_from_cte_xml(xml_assinado) or self._cuf_from_filial()
        xml_cte = self._montar_cte(xml_assinado)
        xml_envi_cte = self._montar_envi_cte(xml_assinado)

        envelope_12_raw_nowrap = self._build_envelope(
            xml_envi_cte, cuf=cuf, wsdl_ns=wsdl_ns, versao_dados="4.00", payload_mode="raw"
        )
        envelope_12_gzip_b64_nowrap = self._build_envelope(
            xml_envi_cte, cuf=cuf, wsdl_ns=wsdl_ns, versao_dados="4.00", payload_mode="gzip_base64"
        )
        envelope_12_gzip_b64_cte_nowrap = self._build_envelope(
            xml_cte, cuf=cuf, wsdl_ns=wsdl_ns, versao_dados="4.00", payload_mode="gzip_base64"
        )
        envelope_12_b64_nowrap = self._build_envelope(
            xml_envi_cte, cuf=cuf, wsdl_ns=wsdl_ns, versao_dados="4.00", payload_mode="base64"
        )
        envelope_12_cdata_nowrap = self._build_envelope(
            xml_envi_cte, cuf=cuf, wsdl_ns=wsdl_ns, versao_dados="4.00", payload_mode="cdata"
        )
        envelope_12_escaped_nowrap = self._build_envelope(
            xml_envi_cte, cuf=cuf, wsdl_ns=wsdl_ns, versao_dados="4.00", payload_mode="escaped"
        )

        envelope_12_gzip_b64 = self._build_envelope(
            xml_envi_cte, cuf=cuf, wsdl_ns=wsdl_ns, versao_dados="4.00", payload_mode="gzip_base64", operation="cteRecepcaoSinc"
        )
        envelope_12_gzip_b64_cte = self._build_envelope(
            xml_cte, cuf=cuf, wsdl_ns=wsdl_ns, versao_dados="4.00", payload_mode="gzip_base64", operation="cteRecepcaoSinc"
        )
        envelope_12_gzip_b64_nohdr = self._build_envelope(
            xml_envi_cte, cuf=cuf, wsdl_ns=wsdl_ns, versao_dados="4.00", payload_mode="gzip_base64", operation="cteRecepcaoSinc", omit_header=True
        )
        envelope_12_b64 = self._build_envelope(
            xml_envi_cte, cuf=cuf, wsdl_ns=wsdl_ns, versao_dados="4.00", payload_mode="base64", operation="cteRecepcaoSinc"
        )
        envelope_12_raw = self._build_envelope(
            xml_envi_cte, cuf=cuf, wsdl_ns=wsdl_ns, versao_dados="4.00", payload_mode="raw", operation="cteRecepcaoSinc"
        )
        envelope_12_cdata = self._build_envelope(
            xml_envi_cte, cuf=cuf, wsdl_ns=wsdl_ns, versao_dados="4.00", payload_mode="cdata", operation="cteRecepcaoSinc"
        )
        envelope_12_escaped = self._build_envelope(
            xml_envi_cte, cuf=cuf, wsdl_ns=wsdl_ns, versao_dados="4.00", payload_mode="escaped", operation="cteRecepcaoSinc"
        )
        envelope_11_raw_nowrap = self._build_envelope(
            xml_envi_cte,
            cuf=cuf,
            wsdl_ns=wsdl_ns,
            versao_dados="4.00",
            soap_env=SOAP_ENV_11,
            payload_mode="raw",
        )
        envelope_11_gzip_b64_nowrap = self._build_envelope(
            xml_envi_cte,
            cuf=cuf,
            wsdl_ns=wsdl_ns,
            versao_dados="4.00",
            soap_env=SOAP_ENV_11,
            payload_mode="gzip_base64",
        )
        envelope_11_gzip_b64_cte_nowrap = self._build_envelope(
            xml_cte,
            cuf=cuf,
            wsdl_ns=wsdl_ns,
            versao_dados="4.00",
            soap_env=SOAP_ENV_11,
            payload_mode="gzip_base64",
        )
        envelope_11_b64_nowrap = self._build_envelope(
            xml_envi_cte,
            cuf=cuf,
            wsdl_ns=wsdl_ns,
            versao_dados="4.00",
            soap_env=SOAP_ENV_11,
            payload_mode="base64",
        )
        envelope_11_cdata_nowrap = self._build_envelope(
            xml_envi_cte,
            cuf=cuf,
            wsdl_ns=wsdl_ns,
            versao_dados="4.00",
            soap_env=SOAP_ENV_11,
            payload_mode="cdata",
        )
        envelope_11_escaped_nowrap = self._build_envelope(
            xml_envi_cte,
            cuf=cuf,
            wsdl_ns=wsdl_ns,
            versao_dados="4.00",
            soap_env=SOAP_ENV_11,
            payload_mode="escaped",
        )

        envelope_11_gzip_b64 = self._build_envelope(
            xml_envi_cte,
            cuf=cuf,
            wsdl_ns=wsdl_ns,
            versao_dados="4.00",
            soap_env=SOAP_ENV_11,
            payload_mode="gzip_base64",
            operation="cteRecepcaoSinc",
        )
        envelope_11_gzip_b64_cte = self._build_envelope(
            xml_cte,
            cuf=cuf,
            wsdl_ns=wsdl_ns,
            versao_dados="4.00",
            soap_env=SOAP_ENV_11,
            payload_mode="gzip_base64",
            operation="cteRecepcaoSinc",
        )
        envelope_11_gzip_b64_nohdr = self._build_envelope(
            xml_envi_cte,
            cuf=cuf,
            wsdl_ns=wsdl_ns,
            versao_dados="4.00",
            soap_env=SOAP_ENV_11,
            payload_mode="gzip_base64",
            operation="cteRecepcaoSinc",
            omit_header=True,
        )
        envelope_11_b64 = self._build_envelope(
            xml_envi_cte,
            cuf=cuf,
            wsdl_ns=wsdl_ns,
            versao_dados="4.00",
            soap_env=SOAP_ENV_11,
            payload_mode="base64",
            operation="cteRecepcaoSinc",
        )
        envelope_11_raw = self._build_envelope(
            xml_envi_cte,
            cuf=cuf,
            wsdl_ns=wsdl_ns,
            versao_dados="4.00",
            soap_env=SOAP_ENV_11,
            payload_mode="raw",
            operation="cteRecepcaoSinc",
        )
        envelope_11_cdata = self._build_envelope(
            xml_envi_cte,
            cuf=cuf,
            wsdl_ns=wsdl_ns,
            versao_dados="4.00",
            soap_env=SOAP_ENV_11,
            payload_mode="cdata",
            operation="cteRecepcaoSinc",
        )
        envelope_11_escaped = self._build_envelope(
            xml_envi_cte,
            cuf=cuf,
            wsdl_ns=wsdl_ns,
            versao_dados="4.00",
            soap_env=SOAP_ENV_11,
            payload_mode="escaped",
            operation="cteRecepcaoSinc",
        )

        # Ordem de tentativas: (soap_version, envelope, soap_action, label)
        tentativas = [
            ("1.2", envelope_12_raw_nowrap, None, "soap12/raw-nowrapper"),
            ("1.2", envelope_12_cdata_nowrap, None, "soap12/cdata-nowrapper"),
            ("1.2", envelope_12_escaped_nowrap, None, "soap12/escaped-nowrapper"),
            ("1.2", envelope_12_gzip_b64_nowrap, None, "soap12/gzip+base64-nowrapper"),
            ("1.2", envelope_12_gzip_b64_cte_nowrap, None, "soap12/gzip+base64-cte-nowrapper"),
            ("1.2", envelope_12_b64_nowrap, None, "soap12/base64-nowrapper"),
            ("1.2", envelope_12_raw_nowrap, f"{wsdl_ns}/cteRecepcaoSinc", "soap12/raw-nowrapper+action"),
            ("1.2", envelope_12_gzip_b64_nowrap, f"{wsdl_ns}/cteRecepcaoSinc", "soap12/gzip+base64-nowrapper+action"),
            ("1.2", envelope_12_gzip_b64, None, "soap12/gzip+base64"),
            ("1.2", envelope_12_gzip_b64_cte, None, "soap12/gzip+base64-cte"),
            ("1.2", envelope_12_gzip_b64_nohdr, None, "soap12/gzip+base64-noheader"),
            ("1.2", envelope_12_b64, None, "soap12/base64"),
            ("1.2", envelope_12_raw, None, "soap12/raw"),
            ("1.2", envelope_12_cdata, None, "soap12/cdata"),
            ("1.2", envelope_12_escaped, None, "soap12/escaped"),
            ("1.1", envelope_11_raw_nowrap, "", "soap11/raw-nowrapper+SOAPAction-empty"),
            ("1.1", envelope_11_cdata_nowrap, "", "soap11/cdata-nowrapper+SOAPAction-empty"),
            ("1.1", envelope_11_escaped_nowrap, "", "soap11/escaped-nowrapper+SOAPAction-empty"),
            ("1.1", envelope_11_gzip_b64_nowrap, "", "soap11/gzip+base64-nowrapper+SOAPAction-empty"),
            ("1.1", envelope_11_gzip_b64_cte_nowrap, "", "soap11/gzip+base64-cte-nowrapper+SOAPAction-empty"),
            ("1.1", envelope_11_b64_nowrap, "", "soap11/base64-nowrapper+SOAPAction-empty"),
            ("1.1", envelope_11_raw_nowrap, "cteRecepcaoSinc", "soap11/raw-nowrapper+SOAPAction-cteRecepcaoSinc"),
            ("1.1", envelope_11_gzip_b64_nowrap, "cteRecepcaoSinc", "soap11/gzip+base64-nowrapper+SOAPAction-cteRecepcaoSinc"),
            ("1.1", envelope_11_gzip_b64, "", "soap11/gzip+base64+SOAPAction-empty"),
            ("1.1", envelope_11_gzip_b64_cte, "", "soap11/gzip+base64-cte+SOAPAction-empty"),
            ("1.1", envelope_11_gzip_b64_nohdr, "", "soap11/gzip+base64-noheader+SOAPAction-empty"),
            ("1.1", envelope_11_b64, "", "soap11/base64+SOAPAction-empty"),
            ("1.1", envelope_11_raw, "", "soap11/raw+SOAPAction-empty"),
            ("1.1", envelope_11_cdata, "", "soap11/cdata+SOAPAction-empty"),
            ("1.1", envelope_11_escaped, "", "soap11/escaped+SOAPAction-empty"),
        ]

        resp_xml = self._tentar_soap(url=url, tentativas=tentativas, cert=(cert_pem_path, key_pem_path))
        return self._processar_retorno_xml(resp_xml)

    # ------------------------------------------------------------------
    # CONSULTA
    # ------------------------------------------------------------------

    def consultar_recibo(self, numero_recibo: str) -> dict:
        """Consulta o processamento de um lote pelo número do recibo."""
        if getattr(self.cte, "chave_de_acesso", None):
            return self.consultar_chave(self.cte.chave_de_acesso)
        raise Exception("Consulta por recibo não suportada neste fluxo. Use consulta por chave.")

    def consultar_chave(self, chave: str) -> dict:
        """Consulta o status do CT-e pela chave de acesso."""
        ambiente = self._ambiente()
        cert_pem_path, key_pem_path = self._get_cert_pem_and_key_pem()
        uf = self._uf()

        url = self._get_url(uf=uf, ambiente=ambiente, servico="consulta")
        wsdl_ns = "http://www.portalfiscal.inf.br/cte/wsdl/CTeConsultaV4"

        cuf = self._cuf_from_filial()
        xml_consulta = self._montar_consulta_chave(chave=chave, ambiente=ambiente)

        envelope_12 = self._build_envelope(
            xml_consulta, cuf=cuf, wsdl_ns=wsdl_ns, versao_dados="4.00", operation="cteConsultaCTe"
        )
        envelope_11 = self._build_envelope(
            xml_consulta, cuf=cuf, wsdl_ns=wsdl_ns, versao_dados="4.00", soap_env=SOAP_ENV_11, operation="cteConsultaCTe"
        )

        # Ordem de tentativas: (soap_version, envelope, soap_action)
        tentativas = [
            ("1.2", envelope_12, None),
            ("1.2", envelope_12, f"{wsdl_ns}/cteConsultaCTe"),
            ("1.1", envelope_11, ""),
            ("1.1", envelope_11, "cteConsultaCTe"),
            ("1.1", envelope_11, f"{wsdl_ns}/cteConsultaCTe"),
        ]

        resp_xml = self._tentar_soap(url=url, tentativas=tentativas, cert=(cert_pem_path, key_pem_path))
        return self._processar_retorno_xml(resp_xml)

    # ------------------------------------------------------------------
    # HELPER: loop de tentativas SOAP
    # ------------------------------------------------------------------

    def _tentar_soap(self, *, url: str, tentativas: list, cert) -> bytes:
        """
        Itera sobre as combinações (version, envelope, action) até obter
        uma resposta válida. Lança a última exceção se todas falharem.
        """
        last_error = None
        last_resp = None
        for t in tentativas:
            if len(t) == 4:
                version, envelope, action, label = t
            else:
                version, envelope, action = t
                label = None
            try:
                resp = self._post_soap(
                    url=url,
                    envelope=envelope,
                    cert=cert,
                    proxies=self._proxies(),
                    soap_action=action,
                    soap_version=version,
                )
                last_resp = resp
                try:
                    c_stat, x_motivo, _, _, _ = self._parse_retorno(resp)
                except Exception:
                    c_stat, x_motivo = "", ""

                logger.info(
                    f"SOAP OK (version={version}, action={action!r}, label={label!r}) "
                    f"cStat={c_stat!r} xMotivo={x_motivo!r}"
                )

                if c_stat in {"244", "215"}:
                    msg = x_motivo or "Falha na descompactacao da area de dados"
                    raise Exception(f"cStat {c_stat}: {msg}")
                return resp
            except Exception as e:
                last_error = e
                logger.warning(f"Tentativa SOAP falhou (version={version}, action={action!r}, label={label!r}): {e}")
                continue

        if last_resp:
            try:
                c_stat, x_motivo, _, _, _ = self._parse_retorno(last_resp)
                raise Exception(f"SEFAZ rejeitou: cStat={c_stat or '000'} xMotivo={x_motivo or 'Erro desconhecido'}")
            except Exception:
                pass

        raise last_error

    # ------------------------------------------------------------------
    # HELPERS internos
    # ------------------------------------------------------------------

    def _ambiente(self) -> str:
        val = getattr(self.filial, "empr_ambi_cte", None)
        if val is None or str(val).strip() == "":
            val = getattr(self.filial, "empr_ambi_nfe", None)
        val = str(val or "2").strip()
        return "1" if val == "1" else "2"

    def _resolve_verify(self):
        bundle = os.getenv("SEFAZ_CA_BUNDLE")
        if bundle and os.path.isfile(bundle):
            return bundle
        verify_env = os.getenv("SEFAZ_VERIFY", "").strip().lower()
        if verify_env in {"false", "0", "off", "no"}:
            return False
        return True

    def _uf(self) -> str:
        uf = str(getattr(self.filial, "empr_esta", "") or "").strip().upper()
        if uf:
            return uf
        raise Exception("UF da filial não informada para seleção do WebService.")

    def _cuf_from_filial(self) -> str:
        cuf = str(getattr(self.filial, "empr_codi_uf", "") or "").strip()
        return cuf.zfill(2) if cuf.isdigit() else ""

    def _cuf_from_cte_xml(self, xml_cte: str) -> str:
        try:
            xml_cte = self._normalizar_xml(xml_cte)
            root = etree.fromstring(xml_cte.encode("utf-8"))
            ns = {"cte": CTE_NS}
            cuf = (root.findtext(".//cte:cUF", namespaces=ns) or "").strip()
            return cuf.zfill(2) if cuf.isdigit() else ""
        except Exception:
            return ""

    def _get_url(self, *, uf: str, ambiente: str, servico: str) -> str:
        ambiente_key = "producao" if ambiente == "1" else "homologacao"
        data = URLS_SEFAZ_CTE.get(uf, {}).get(ambiente_key, {})
        url = data.get(servico)
        if not url:
            raise Exception(
                f"URL SEFAZ CT-e não configurada para UF={uf} ambiente={ambiente_key} serviço={servico}."
            )
        return url

    def _proxies(self):
        host = str(getattr(self.filial, "empr_prox_host_cte", "") or "").strip()
        port = str(getattr(self.filial, "empr_prox_port_cte", "") or "").strip()
        user = str(getattr(self.filial, "empr_prox_user_cte", "") or "").strip()
        password = str(getattr(self.filial, "empr_prox_pass_cte", "") or "").strip()

        if not host or not port:
            return None

        auth = f"{user}:{password}@" if user and password else ""
        proxy = f"http://{auth}{host}:{port}"
        return {"http": proxy, "https": proxy}

    def _get_cert_pem_and_key_pem(self):
        caminho_certificado, senha_certificado = CertificadoLoader(self.filial).load()
        if not caminho_certificado:
            raise Exception("Certificado digital não configurado/indisponível.")

        with open(caminho_certificado, "rb") as f:
            pfx_bytes = f.read()

        password = (senha_certificado or "").encode("utf-8") if senha_certificado else None
        key, cert, addl = pkcs12.load_key_and_certificates(pfx_bytes, password)
        if key is None or cert is None:
            raise Exception("Certificado A1 inválido ou incompleto.")

        key_pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
        cert_pem = cert.public_bytes(Encoding.PEM)
        if addl:
            for c in addl:
                try:
                    cert_pem += c.public_bytes(Encoding.PEM)
                except Exception:
                    pass

        cert_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
        cert_file.write(cert_pem)
        cert_file.flush()

        key_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
        key_file.write(key_pem)
        key_file.flush()

        return cert_file.name, key_file.name

    def _build_envelope(
        self,
        xml_payload: str,
        *,
        cuf: str,
        wsdl_ns: str,
        versao_dados: str,
        soap_env: str = None,
        payload_mode: str = "raw",
        operation: str = None,
        omit_header: bool = False,
    ) -> str:
        cuf_txt = (cuf or "").strip()
        soap_env = soap_env or SOAP_ENV
        payload = (xml_payload or "").strip()
        if payload_mode == "gzip_base64":
            import gzip
            import base64

            raw = payload.encode("utf-8")
            gz = gzip.compress(raw)
            payload = base64.b64encode(gz).decode("ascii")
        elif payload_mode == "base64":
            import base64

            payload = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        elif payload_mode == "cdata":
            payload = f"<![CDATA[{payload}]]>"
        elif payload_mode == "escaped":
            from xml.sax.saxutils import escape

            payload = escape(payload)

        op = operation or ""
        if op:
            body_inner = (
                f'<ws:{op} xmlns:ws="{wsdl_ns}">'
                f'<ws:cteDadosMsg>'
                f"{payload}"
                f'</ws:cteDadosMsg>'
                f'</ws:{op}>'
            )
        else:
            body_inner = (
                f'<ws:cteDadosMsg xmlns:ws="{wsdl_ns}">'
                f"{payload}"
                f'</ws:cteDadosMsg>'
            )

        header = ""
        if not omit_header:
            header = (
                f'<env:Header>'
                f'<ws:cteCabecMsg xmlns:ws="{wsdl_ns}">'
                f'<ws:cUF>{cuf_txt}</ws:cUF>'
                f'<ws:versaoDados>{versao_dados}</ws:versaoDados>'
                f'</ws:cteCabecMsg>'
                f'</env:Header>'
            )

        envelope = (
            f'<env:Envelope xmlns:env="{soap_env}">'
            f"{header}"
            f'<env:Body>'
            f"{body_inner}"
            f'</env:Body>'
            f'</env:Envelope>'
        )
        return envelope

    def _post_soap(
        self,
        *,
        url: str,
        envelope: str,
        cert,
        proxies=None,
        soap_action: str = None,
        soap_version: str = "1.2",
    ) -> bytes:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 502, 503, 504],
            allowed_methods=["POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        if soap_version == "1.1":
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": f'"{soap_action or ""}"',
            }
        else:
            content_type = "application/soap+xml; charset=utf-8"
            if soap_action:
                content_type = f'{content_type}; action="{soap_action}"'
            headers = {"Content-Type": content_type}

        resp = session.post(
            url,
            data=envelope.encode("utf-8"),
            headers=headers,
            cert=cert,
            verify=self._resolve_verify(),
            timeout=30,
            proxies=proxies,
        )

        if not resp.content:
            raise Exception("SEFAZ não retornou resposta.")

        if resp.status_code >= 400:
            raise Exception(f"HTTP {resp.status_code} ao comunicar com SEFAZ. {resp.text}")

        # SOAP Fault pode vir com HTTP 200 — detectar pelo conteúdo
        content = resp.content
        content_lower = content.lower()
        if b"faultcode" in content_lower or b"faultstring" in content_lower:
            try:
                fault_text = content.decode("utf-8", errors="replace")
            except Exception:
                fault_text = str(content)
            raise Exception(f"SOAP Fault: {fault_text}")

        return content

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

    def _parse_cte_root(self, xml_cte_assinado: str):
        xml = self._normalizar_xml(xml_cte_assinado)
        parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False)
        try:
            cte_root = etree.fromstring(xml.encode("utf-8"), parser=parser)
        except Exception as e:
            raise Exception(f"XML do CT-e inválido (antes do envio): {e}")

        if etree.QName(cte_root).localname != "CTe":
            raise Exception("XML assinado inválido: raiz deve ser <CTe>.")
        if etree.QName(cte_root).namespace != CTE_NS:
            raise Exception("XML assinado inválido: namespace do <CTe> deve ser o do CT-e.")
        return cte_root

    def _montar_cte(self, xml_cte_assinado: str) -> str:
        cte_root = self._parse_cte_root(xml_cte_assinado)
        return etree.tostring(cte_root, encoding="unicode", xml_declaration=False)

    def _montar_envi_cte(self, xml_cte_assinado: str) -> str:
        cte_root = self._parse_cte_root(xml_cte_assinado)

        id_lote = str(getattr(self.cte, "numero", "") or "").strip()
        if not id_lote or not id_lote.isdigit():
            id_lote = "1"

        envi = etree.Element(f"{{{CTE_NS}}}enviCTe", nsmap={None: CTE_NS}, versao="4.00")
        id_lote_el = etree.SubElement(envi, f"{{{CTE_NS}}}idLote")
        id_lote_el.text = id_lote
        ind_sinc_el = etree.SubElement(envi, f"{{{CTE_NS}}}indSinc")
        ind_sinc_el.text = "1"
        envi.append(cte_root)
        return etree.tostring(envi, encoding="unicode", xml_declaration=False)

    def _montar_consulta_chave(self, *, chave: str, ambiente: str) -> str:
        tp_amb = "1" if ambiente == "1" else "2"
        return (
            f'<consSitCTe xmlns="{CTE_NS}" versao="4.00">'
            f"<tpAmb>{tp_amb}</tpAmb>"
            f"<xServ>CONSULTAR</xServ>"
            f"<chCTe>{chave}</chCTe>"
            f"</consSitCTe>"
        )

    def _parse_retorno(self, xml_bytes: bytes):
        root = etree.fromstring(xml_bytes)

        def first_text(xpath_expr: str):
            try:
                vals = root.xpath(xpath_expr)
                for v in vals:
                    t = v.strip() if isinstance(v, str) else (v.text or "").strip()
                    if t:
                        return t
            except Exception:
                return ""
            return ""

        c_stat = first_text('//*[local-name()="cStat"][1]')
        x_motivo = first_text('//*[local-name()="xMotivo"][1]') or "Erro desconhecido"
        n_prot = first_text('//*[local-name()="nProt"][1]') or None
        n_rec = first_text('//*[local-name()="nRec"][1]') or None

        xml_protocolo = None
        try:
            ns = {"cte": CTE_NS}
            prot = root.find(".//cte:protCTe", namespaces=ns)
            if prot is None:
                prot = root.find(".//{*}protCTe")
            if prot is not None:
                xml_protocolo = etree.tostring(prot, encoding="unicode")
        except Exception:
            xml_protocolo = None

        return c_stat, x_motivo, n_prot, n_rec, xml_protocolo

    def _processar_retorno_xml(self, xml_bytes: bytes) -> dict:
        c_stat, x_motivo, n_prot, n_rec, xml_protocolo = self._parse_retorno(xml_bytes)
        try:
            logger.info(f"Retorno SEFAZ: cStat={c_stat!r} xMotivo={x_motivo!r} nProt={n_prot!r} nRec={n_rec!r}")
        except Exception:
            pass

        if not c_stat:
            try:
                txt = xml_bytes.decode("utf-8", errors="replace")
            except Exception:
                txt = str(xml_bytes)
            txt = (txt or "").strip()
            if len(txt) > 2000:
                txt = txt[:2000] + "..."
            logger.warning(f"Retorno SEFAZ sem cStat (primeiros chars): {txt}")

        if c_stat == "100":
            return {
                "status": "autorizado",
                "protocolo": n_prot,
                "mensagem": x_motivo,
                "xml_protocolo": xml_protocolo,
            }
        if c_stat == "103":
            return {
                "status": "recebido",
                "recibo": n_rec,
                "mensagem": x_motivo,
                "xml_protocolo": xml_protocolo,
            }
        if c_stat == "104":
            if n_prot:
                return {
                    "status": "autorizado",
                    "protocolo": n_prot,
                    "mensagem": x_motivo,
                    "xml_protocolo": xml_protocolo,
                }
            return {
                "status": "rejeitado",
                "codigo": c_stat,
                "mensagem": x_motivo,
                "xml_protocolo": xml_protocolo,
            }
        if c_stat in ["105", "106"]:
            return {
                "status": "processando",
                "mensagem": x_motivo,
                "xml_protocolo": xml_protocolo,
            }
        return {
            "status": "rejeitado",
            "codigo": c_stat or "000",
            "mensagem": x_motivo,
            "xml_protocolo": xml_protocolo,
        }
