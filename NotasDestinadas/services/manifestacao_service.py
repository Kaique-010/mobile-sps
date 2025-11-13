import logging

try:
    from pynfe.utils import FileUtils
except Exception:
    FileUtils = None
try:
    from pynfe.processamento.comunicacao import Comunicacao
except Exception:
    Comunicacao = None

from ..models import NotaFiscalEntrada

logger = logging.getLogger(__name__)


class ManifestacaoService:
    """
    Serviço de manifestação do destinatário.
    Exemplo: 210200 - Ciência da Operação.
    """

    @classmethod
    def _get_comunicacao(cls, uf: str, caminho_pfx: str, senha_pfx: str, ambiente: int = 1):
        if not Comunicacao:
            raise RuntimeError('Biblioteca pynfe indisponível')
        cert = FileUtils.read_pfx(caminho_pfx, senha_pfx) if (FileUtils and hasattr(FileUtils, 'read_pfx')) else None
        try:
            return Comunicacao(
                uf=uf,
                certificado=cert,
                ambiente=ambiente,
            )
        except Exception:
            return Comunicacao(
                uf=uf,
                caminho_pfx=caminho_pfx,
                senha=senha_pfx,
                ambiente=ambiente,
            )

    @classmethod
    def manifestar_ciencia(
        cls,
        *,
        nota_entrada: NotaFiscalEntrada,
        uf: str,
        cnpj_destinatario: str,
        caminho_pfx: str,
        senha_pfx: str,
        ambiente: int = 1,
        justificativa: str = 'Entrada registrada automaticamente',
    ):
        """
        Envia evento 210200 - Ciência da Operação.
        """
        com = cls._get_comunicacao(uf, caminho_pfx, senha_pfx, ambiente)

        import xml.etree.ElementTree as ET
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        chave = None
        try:
            xml = getattr(nota_entrada, 'xml_nfe', '') or ''
            if xml:
                root = ET.fromstring(xml)
                chave = root.findtext('.//nfe:chNFe', None, ns)
                if not chave:
                    inf = root.find('.//nfe:infNFe', ns)
                    if inf is not None:
                        ident = (inf.attrib.get('Id') or '').strip()
                        if ident.startswith('NFe') and len(ident) >= 47:
                            chave = ident[3:]
        except Exception:
            chave = None
        if not chave:
            raise RuntimeError('Chave de acesso da NF-e não encontrada no XML')

        logger.info(f'Manifestando ciência da operação para NF-e chave={chave} empresa={nota_entrada.empresa}')

        resp = com.manifestacao_destinatario(
            cnpj=cnpj_destinatario,
            chave_nfe=chave,
            tipo_evento='210200',  # Ciência da Operação
            justificativa=justificativa,
        )

        protocolo = getattr(resp, 'protocolo', None)

        nota_entrada.status_nfe = 210200
        nota_entrada.protocolo_nfe = protocolo or nota_entrada.protocolo_nfe
        nota_entrada.save()

        logger.info(f'Manifestação registrada. protocolo={protocolo}')
        return resp
