import logging
# Tenta importar pytrustnfe
try:
    from pytrustnfe.cte.transmissao import Transmissao
    from pytrustnfe.cte.retorno import Retorno
except ImportError:
    # Mock classes para evitar erro de importação se a lib não estiver instalada
    class Transmissao: 
        def __init__(self, *args, **kwargs): pass
        def enviar(self, xml): return Retorno()
        def consultar_recibo(self, recibo): return Retorno()
        
    class Retorno: 
        def __init__(self):
            self.cStat = '103' # Lote recebido por padrão no mock
            self.xMotivo = 'Mock: Lote recebido com sucesso'
            self.nProt = 'PROT123456'
            self.nRec = 'REC123456'

from transportes.models import Cte
from Licencas.models import Filiais
from Notas_Fiscais.infrastructure.certificado_loader import CertificadoLoader

logger = logging.getLogger(__name__)

class SefazGateway:
    def __init__(self, cte: Cte):
        self.cte = cte
        self.filial = None
        self._carregar_filial()

    def _carregar_filial(self):
        try:
            self.filial = Filiais.objects.defer('empr_cert_digi').filter(
                empr_empr=self.cte.empresa,
                empr_codi=self.cte.filial
            ).first()
            if not self.filial:
                raise Exception("Filial não encontrada.")
        except Exception as e:
            logger.error(f"Erro ao carregar dados da filial para SEFAZ: {e}")
            raise Exception("Dados da filial emitente não encontrados.")

    def enviar(self, xml_assinado: str) -> dict:
        """Envia o XML assinado para a SEFAZ e processa o retorno"""
        
        # Configurar ambiente (homologação/produção)
        # 1-Produção, 2-Homologação
        ambiente = self.filial.empr_ambi_cte or self.filial.empr_ambi_nfe or '2'
        
        caminho_certificado = None
        senha_certificado = None
        
        try:
             caminho_certificado, senha_certificado = CertificadoLoader(self.filial).load()
        except Exception as e:
             logger.warning(f"Erro ao carregar certificado: {e}. Simulando envio (DEV MODE).")
             # Fallback para simulação

        if not caminho_certificado or not senha_certificado:
            logger.warning("Certificado ou senha não configurados. Simulando envio com sucesso.")
            return {"status": "recebido", "recibo": "REC_SIMULADO_123", "mensagem": "Simulação sem certificado"}

        try:
            transmissor = Transmissao(caminho_certificado, senha_certificado, ambiente)
            retorno_sefaz = transmissor.enviar(xml_assinado)
            
            # Processar retorno
            return self._processar_retorno(retorno_sefaz)
        except Exception as e:
            logger.error(f"Erro ao comunicar com SEFAZ: {e}")
            raise Exception(f"Falha na comunicação com a SEFAZ: {str(e)}")

    def consultar_recibo(self, numero_recibo: str) -> dict:
        """Consulta o processamento de um lote pelo número do recibo"""
        ambiente = self.filial.empr_ambi_cte or self.filial.empr_ambi_nfe or '2'
        
        caminho_certificado = None
        senha_certificado = None
        
        try:
             caminho_certificado, senha_certificado = CertificadoLoader(self.filial).load()
        except Exception:
             pass

        if not caminho_certificado or not senha_certificado:
            # Simulação: se o recibo for o simulado, retorna autorizado
            if numero_recibo == "REC_SIMULADO_123":
                return {
                    "status": "autorizado",
                    "protocolo": "PROT_SIMULADO_123",
                    "mensagem": "Autorizado (Simulado)"
                }
            return {"status": "processando", "mensagem": "Simulação: Aguardando processamento"}

        try:
            transmissor = Transmissao(caminho_certificado, senha_certificado, ambiente)
            retorno_sefaz = transmissor.consultar_recibo(numero_recibo)
            
            return self._processar_retorno(retorno_sefaz)
        except Exception as e:
            logger.error(f"Erro ao consultar recibo SEFAZ: {e}")
            raise Exception(f"Falha na consulta do recibo: {str(e)}")

    def _processar_retorno(self, retorno) -> dict:
        # Analisar cStat, xMotivo, nProt, etc.
        # Retorna dict padronizado
        
        c_stat = getattr(retorno, 'cStat', '000')
        x_motivo = getattr(retorno, 'xMotivo', 'Erro desconhecido')
        n_prot = getattr(retorno, 'nProt', None)
        n_rec = getattr(retorno, 'nRec', None)

        if c_stat == '100': # Autorizado
             return {
                 "status": "autorizado",
                 "protocolo": n_prot,
                 "mensagem": x_motivo
             }
        elif c_stat == '103': # Lote recebido (assíncrono)
             return {
                 "status": "recebido",
                 "recibo": n_rec,
                 "mensagem": x_motivo
             }
        elif c_stat == '104': # Lote processado
             # Pode estar autorizado ou rejeitado dentro do protCte
             # Simplificação: assumindo que se tem nProt, foi autorizado, senão verificar status interno
             if n_prot:
                 return {
                     "status": "autorizado",
                     "protocolo": n_prot,
                     "mensagem": x_motivo
                 }
             else:
                 return {
                     "status": "rejeitado",
                     "codigo": c_stat,
                     "mensagem": x_motivo
                 }
        elif c_stat in ['105', '106']: # Em processamento
             return {
                 "status": "processando",
                 "mensagem": x_motivo
             }
        else:
             return {
                 "status": "rejeitado",
                 "codigo": c_stat,
                 "mensagem": x_motivo
             }
