# emissao_service.py
from datetime import datetime
from transportes.models import Cte
from transportes.services.validacao_service import ValidacaoService
from transportes.services.numeracao_service import NumeracaoService
from transportes.builders.cte_xml_builder import CteXmlBuilder
from transportes.services.assinatura_service import AssinaturaService
from transportes.services.sefaz_gateway import SefazGateway

class EmissaoService:
    def __init__(self, cte: Cte, slug=None):
        self.cte = cte
        self.slug = slug
        self.validador = ValidacaoService(cte)
        self.numerador = NumeracaoService(cte.empresa, cte.filial, cte.serie, slug=slug)
        self.xml_builder = CteXmlBuilder(cte)
        self.assinador = AssinaturaService(cte)
        self.gateway = SefazGateway(cte)

    def emitir(self):
        """
        Orquestra o fluxo de emissão do CTe:
        1. Validação Completa
        2. Geração de Numeração (se necessário)
        3. Construção do XML
        4. Assinatura Digital
        5. Envio para SEFAZ
        6. Atualização de Status
        """
        # 1. Validar
        if not self.validador.validar_emissao():
            raise Exception("Falha na validação do CTe: " + str(self.validador.get_errors()))

        # 2. Gerar Número (se ainda não tiver)
        if not self.cte.numero:
            novo_numero = self.numerador.proximo_numero()
            self.cte.numero = novo_numero
            self.cte.save()

        # 3. Gerar XML
        try:
            xml_conteudo = self.xml_builder.build()
            self.cte.xml_cte = xml_conteudo
            self.cte.save()
        except Exception as e:
            raise Exception(f"Erro ao gerar XML: {str(e)}")

        # 4. Assinar XML
        try:
            xml_assinado = self.assinador.assinar(xml_conteudo)
            self.cte.xml_cte = xml_assinado # Atualiza com XML assinado
            self.cte.save()
        except Exception as e:
            raise Exception(f"Erro ao assinar XML: {str(e)}")

        # 5. Enviar para SEFAZ
        try:
            resultado_envio = self.gateway.enviar(xml_assinado)
        except Exception as e:
            # Em caso de falha de comunicação, manter status atual ou marcar erro de transmissão
            raise Exception(f"Erro ao enviar para SEFAZ: {str(e)}")
        
        # 6. Atualizar Status com base no retorno
        if resultado_envio.get('status') == 'autorizado':
             self._processar_autorizacao(resultado_envio)
        elif resultado_envio.get('status') == 'recebido':
             self.cte.status = 'REC' # Recebido/Em processamento
             self.cte.save()
             
             # Loop de consulta do recibo
             recibo = resultado_envio.get('recibo')
             if recibo:
                 import time
                 import logging
                 logger = logging.getLogger(__name__)
                 
                 # Tenta consultar até 5 vezes (aprox. 10-15s)
                 for i in range(5):
                     time.sleep(2) # Espera 2s entre tentativas
                     try:
                         logger.info(f"Consultando recibo {recibo} (tentativa {i+1}/5)...")
                         retorno_consulta = self.gateway.consultar_recibo(recibo)
                         
                         # Processar autorização se encontrada
                         status_consulta = retorno_consulta.get('status')
                         if status_consulta == 'autorizado':
                             self._processar_autorizacao(retorno_consulta)
                             resultado_envio = retorno_consulta # Atualiza retorno final
                             break
                         elif status_consulta == 'rejeitado':
                             self.cte.status = 'REJ'
                             # Salvar motivo se possível (hoje não temos campo específico além de log/retorno)
                             self.cte.save()
                             resultado_envio = retorno_consulta
                             break
                         elif status_consulta == 'processando':
                             continue # Tenta novamente
                         else:
                             # Status desconhecido, mantém REC
                             logger.warning(f"Status desconhecido na consulta: {status_consulta}")
                             
                     except Exception as e:
                         logger.error(f"Erro ao consultar recibo {recibo}: {e}")
                         # Continua tentando em caso de erro de rede temporário
                         continue

        elif resultado_envio.get('status') == 'rejeitado':
             self.cte.status = 'REJ'
             # Salvar motivo da rejeição se houver campo
             # self.cte.motivo_rejeicao = resultado_envio.get('mensagem')
             self.cte.save()
        
        return resultado_envio

    def _processar_autorizacao(self, resultado):
         self.cte.status = 'AUT'
         self.cte.protocolo = resultado.get('protocolo')
         
         # Constrói o XML de distribuição (cteProc)
         xml_protocolo = resultado.get('xml_protocolo')
         if xml_protocolo and self.cte.xml_cte:
             xml_assinado_str = self.cte.xml_cte
             # Remove declaração XML se existir para não ficar duplicada ou inválida dentro do procCTe
             if xml_assinado_str.strip().startswith('<?xml'):
                 idx = xml_assinado_str.find('>')
                 if idx != -1:
                     xml_assinado_str = xml_assinado_str[idx+1:].strip()
             
             # Verifica se já não está encapsulado (caso de reprocessamento)
             if not xml_assinado_str.strip().startswith('<cteProc'):
                self.cte.xml_cte = f'<cteProc xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">{xml_assinado_str}{xml_protocolo}</cteProc>'
         
         self.cte.save()
