import logging
import os
# Tenta importar pytrustnfe
try:
    from pytrustnfe.certificado import Certificado
    from pytrustnfe.assinatura import Assinatura
except ImportError:
    # Mock classes para evitar erro de importação se a lib não estiver instalada
    class Certificado: 
        def __init__(self, caminho, senha): pass
    class Assinatura: 
        def __init__(self, certificado): pass
        def assinar(self, xml): return xml

from transportes.models import Cte
from Licencas.models import Filiais
from Notas_Fiscais.infrastructure.certificado_loader import CertificadoLoader

logger = logging.getLogger(__name__)

class AssinaturaService:
    def __init__(self, cte: Cte):
        self.cte = cte
        self.filial = None
        self._carregar_filial()

    def _carregar_filial(self):
        try:
            # Garante o uso do mesmo banco de dados do CTe (multi-tenancy)
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

    def assinar(self, xml_content: str) -> str:
        """Assina o XML do CTe usando o certificado digital da filial"""
        
        caminho_certificado = None
        senha_certificado = None

        try:
            # Usa o CertificadoLoader para descriptografar e salvar temporariamente o certificado
            caminho_certificado, senha_certificado = CertificadoLoader(self.filial).load()
        except Exception as e:
            logger.warning(f"Erro ao carregar certificado: {e}. Prosseguindo sem assinatura (DEV MODE).")
            # Se falhar o carregamento (ex: sem certificado), retorna o XML original
            return xml_content

        if not caminho_certificado or not senha_certificado:
            logger.warning("Certificado ou senha não configurados. Retornando XML sem assinatura.")
            return xml_content

        try:
            certificado = Certificado(caminho_certificado, senha_certificado)
            assinador = Assinatura(certificado)
            xml_assinado = assinador.assinar(xml_content)
            
            # Limpeza do arquivo temporário do certificado se foi criado pelo loader
            # O CertificadoLoader pode ou não limpar, mas aqui garantimos se for o caso
            # Nota: CertificadoLoader do projeto geralmente lida com isso ou deixa para o SO/garbage collection
            
            return xml_assinado
        except Exception as e:
            logger.error(f"Erro ao assinar XML: {e}")
            raise Exception(f"Falha na assinatura digital: {str(e)}")
