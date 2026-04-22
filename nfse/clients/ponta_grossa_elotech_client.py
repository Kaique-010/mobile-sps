from xml.etree import ElementTree as ET

from nfse.builders import ElotechXmlBuilder
from nfse.clients.base_client import BaseNfseClient
from nfse.clients.http_client import HttpClient
from nfse.exceptions import NfseClientError, NfseParseError, NfseSoapError


class PontaGrossaElotechClient(BaseNfseClient):
    def __init__(self, config):
        super().__init__(config)
        self.http_client = HttpClient(timeout=60)
        self.builder = ElotechXmlBuilder()

    def montar_xml_envio_emissao(self, data: dict) -> str:
        xml_conteudo = self.builder.montar_xml_emissao(data)
        return self.builder.montar_envelope_soap(xml_conteudo)

    def emitir(self, data: dict):
        envelope = self.montar_xml_envio_emissao(data)

        try:
            response = self._post_soap(
                action=self.config.nfmc_soap_act_emis,
                xml=envelope,
                url=self.config.nfmc_url_emis,
            )
            resultado = self._parse_emissao_response(response.text, xml_envio=envelope, payload=data)
            resultado['xml_envio'] = envelope
            return resultado

        except NfseClientError:
            raise
        except Exception as exc:
            raise NfseClientError(
                f'Erro inesperado ao emitir NFS-e em Ponta Grossa: {exc}',
                payload=data,
                xml_envio=envelope,
            ) from exc

    def consultar(self, **kwargs):
        xml_conteudo = self.builder.montar_xml_consulta(kwargs)
        envelope = self.builder.montar_envelope_soap(xml_conteudo)

        try:
            response = self._post_soap(
                action=self.config.nfmc_soap_act_cons,
                xml=envelope,
                url=self.config.nfmc_url_cons or self.config.nfmc_url_emis,
            )
            resultado = self._parse_consulta_response(response.text, xml_envio=envelope, payload=kwargs)
            resultado['xml_envio'] = envelope
            return resultado

        except NfseClientError:
            raise
        except Exception as exc:
            raise NfseClientError(
                f'Erro inesperado ao consultar NFS-e em Ponta Grossa: {exc}',
                payload=kwargs,
                xml_envio=envelope,
            ) from exc

    def cancelar(self, **kwargs):
        xml_conteudo = self.builder.montar_xml_cancelamento(kwargs)
        envelope = self.builder.montar_envelope_soap(xml_conteudo)

        try:
            response = self._post_soap(
                action=self.config.nfmc_soap_act_canc,
                xml=envelope,
                url=self.config.nfmc_url_canc or self.config.nfmc_url_emis,
            )
            resultado = self._parse_cancelamento_response(response.text, xml_envio=envelope, payload=kwargs)
            resultado['xml_envio'] = envelope
            return resultado

        except NfseClientError:
            raise
        except Exception as exc:
            raise NfseClientError(
                f'Erro inesperado ao cancelar NFS-e em Ponta Grossa: {exc}',
                payload=kwargs,
                xml_envio=envelope,
            ) from exc

    def _post_soap(self, *, action: str | None, xml: str, url: str):
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
        }

        if action:
            headers['SOAPAction'] = action

        auth = None
        if self.config.nfmc_usua and self.config.nfmc_senh:
            auth = (self.config.nfmc_usua, self.config.nfmc_senh)

        return self.http_client.post(
            url=url,
            data=xml,
            headers=headers,
            auth=auth,
        )

    def _parse_emissao_response(self, xml_text: str, *, xml_envio: str | None = None, payload: dict | None = None) -> dict:
        root = self._parse_xml(xml_text, xml_envio=xml_envio, payload=payload)

        fault = self._find_first_text(root, ['faultstring'])
        if fault:
            raise NfseSoapError(
                f'Erro SOAP na emissão: {fault}',
                payload=payload,
                xml_envio=xml_envio,
                xml_retorno=xml_text,
                resposta={'faultstring': fault},
            )

        return {
            'numero': self._find_first_text(root, ['numero', 'Numero', 'nroNota']),
            'codigo_verificacao': self._find_first_text(root, ['codigoVerificacao', 'CodigoVerificacao']),
            'protocolo': self._find_first_text(root, ['protocolo', 'Protocolo']),
            'status': self._find_first_text(root, ['status', 'Status']) or 'emitida',
            'xml_retorno': xml_text,
            'mensagem': self._find_first_text(root, ['mensagem', 'Mensagem']),
            'data_emissao': self._find_first_text(root, ['dataEmissao', 'DataEmissao']),
        }

    def _parse_consulta_response(self, xml_text: str, *, xml_envio: str | None = None, payload: dict | None = None) -> dict:
        root = self._parse_xml(xml_text, xml_envio=xml_envio, payload=payload)

        fault = self._find_first_text(root, ['faultstring'])
        if fault:
            raise NfseSoapError(
                f'Erro SOAP na consulta: {fault}',
                payload=payload,
                xml_envio=xml_envio,
                xml_retorno=xml_text,
                resposta={'faultstring': fault},
            )

        return {
            'numero': self._find_first_text(root, ['numero', 'Numero', 'nroNota']),
            'codigo_verificacao': self._find_first_text(root, ['codigoVerificacao', 'CodigoVerificacao']),
            'protocolo': self._find_first_text(root, ['protocolo', 'Protocolo']),
            'status': self._find_first_text(root, ['status', 'Status']),
            'xml_retorno': xml_text,
            'mensagem': self._find_first_text(root, ['mensagem', 'Mensagem']),
        }

    def _parse_cancelamento_response(self, xml_text: str, *, xml_envio: str | None = None, payload: dict | None = None) -> dict:
        root = self._parse_xml(xml_text, xml_envio=xml_envio, payload=payload)

        fault = self._find_first_text(root, ['faultstring'])
        if fault:
            raise NfseSoapError(
                f'Erro SOAP no cancelamento: {fault}',
                payload=payload,
                xml_envio=xml_envio,
                xml_retorno=xml_text,
                resposta={'faultstring': fault},
            )

        return {
            'status': self._find_first_text(root, ['status', 'Status']) or 'cancelada',
            'mensagem': self._find_first_text(root, ['mensagem', 'Mensagem']),
            'xml_retorno': xml_text,
        }

    def _parse_xml(self, xml_text: str, *, xml_envio: str | None = None, payload: dict | None = None):
        try:
            return ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise NfseParseError(
                f'Retorno XML inválido: {exc}',
                payload=payload,
                xml_envio=xml_envio,
                xml_retorno=xml_text,
            ) from exc

    def _find_first_text(self, root, names: list[str]) -> str | None:
        for elem in root.iter():
            tag_limpa = self._strip_namespace(elem.tag)
            if tag_limpa in names and elem.text:
                return elem.text.strip()
        return None

    def _strip_namespace(self, tag: str) -> str:
        if '}' in tag:
            return tag.split('}', 1)[1]
        return tag