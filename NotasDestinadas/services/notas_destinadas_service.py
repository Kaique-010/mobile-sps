import logging
from typing import List, Tuple, Optional

try:
    from pynfe.utils import FileUtils
except Exception:
    FileUtils = None
try:
    from pynfe.processamento.comunicacao import ComunicacaoSefaz
except Exception:
    ComunicacaoSefaz = None

logger = logging.getLogger(__name__)


class NotasDestinadasService:
    """
    Serviço de consulta de Notas Destinadas (Distribuição DF-e).
    """

    @classmethod
    def _get_certificado(cls, caminho_pfx: str, senha: str):
        """
        Carrega o certificado A1 quando disponível.
        """
        if FileUtils and hasattr(FileUtils, 'read_pfx'):
            return FileUtils.read_pfx(caminho_pfx, senha)
        return None

    @classmethod
    def _get_comunicacao(cls, uf: str, caminho_pfx: str, senha_pfx: str, ambiente: int = 1):
        """
        Cria o objeto de comunicação com a SEFAZ, com fallback quando a API varia.
        """
        if not ComunicacaoSefaz:
            raise RuntimeError('Biblioteca pynfe indisponível')
        homologacao = 2 if int(ambiente or 1) == 2 else 1
        return ComunicacaoSefaz(uf, caminho_pfx, senha_pfx, homologacao == 2)

    @classmethod
    def consultar_notas_destinadas(
        cls,
        *,
        uf: str,
        cnpj: str,
        ultimo_nsu: str,
        caminho_pfx: str,
        senha_pfx: str,
        ambiente: int = 1,
    ) -> Tuple[List[str], Optional[str]]:
        """
        Consulta DF-e e devolve:
        - lista de XMLs completos de NFe
        - novo_ultimo_nsu (para ser salvo e usado na próxima consulta)
        """
        com = cls._get_comunicacao(uf, caminho_pfx, senha_pfx, ambiente)

        import re
        import base64
        import gzip
        import xml.etree.ElementTree as ET

        cnpj_digits = re.sub(r"\D", "", str(cnpj))
        nsu_num = str(ultimo_nsu or '0')
        logger.info(f'Consultando DF-e para CNPJ={cnpj_digits} último_nsu={nsu_num}')

        resp = com.consulta_distribuicao(cnpj=cnpj_digits, nsu=nsu_num, consulta_nsu_especifico=False)

        xmls: List[str] = []
        novo_ultimo_nsu: Optional[str] = None

        try:
            texto = getattr(resp, 'text', None) or getattr(resp, 'content', b'')
            if isinstance(texto, bytes):
                texto = texto.decode('utf-8', errors='ignore')
            root = ET.fromstring(texto)

            def tag(t):
                return t.split('}')[-1]

            ret = None
            for e in root.iter():
                if tag(e.tag) == 'retDistDFeInt':
                    ret = e
                    break
            if ret is not None:
                for e in ret:
                    if tag(e.tag) == 'ultNSU':
                        novo_ultimo_nsu = (e.text or '').strip() or None
                    if tag(e.tag) == 'loteDistDFe':
                        for doc in e.iter():
                            if tag(doc.tag) == 'docZip':
                                schema = doc.attrib.get('schema')
                                conteudo = doc.text or ''
                                try:
                                    dados = base64.b64decode(conteudo)
                                    xml_str = gzip.decompress(dados).decode('utf-8', errors='ignore')
                                except Exception:
                                    xml_str = ''
                                if schema and schema.startswith('procNFe') and xml_str:
                                    xmls.append(xml_str)
        except Exception:
            pass

        logger.info(f'Retorno DF-e: {len(xmls)} XML(s) completos. novo_ultimo_nsu={novo_ultimo_nsu}')
        return xmls, novo_ultimo_nsu
