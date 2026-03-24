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
        db_alias = self.slug or self.cte._state.db or 'default'
        # 1. Validar
        if not self.validador.validar_emissao():
            raise Exception("Falha na validação do CTe: " + str(self.validador.get_errors()))

        # 2. Gerar Número (se ainda não tiver)
        if not self.cte.numero:
            novo_numero = self.numerador.proximo_numero()
            self.cte.numero = novo_numero
            self.cte.save(using=db_alias)

        # 3. Gerar XML
        try:
            xml_conteudo = self.xml_builder.build()
            self.cte.xml_cte = xml_conteudo
            self.cte.save(using=db_alias)
        except Exception as e:
            raise Exception(f"Erro ao gerar XML: {str(e)}")

        # 4. Assinar XML
        try:
            xml_assinado = self.assinador.assinar(xml_conteudo)
            self.cte.xml_cte = xml_assinado # Atualiza com XML assinado
            self.cte.save(using=db_alias)
        except Exception as e:
            raise Exception(f"Erro ao assinar XML: {str(e)}")

        # 5. Enviar para SEFAZ
        try:
            resultado_envio = self.gateway.enviar(xml_assinado)
        except Exception as e:
            # Em caso de falha de comunicação, manter status atual ou marcar erro de transmissão
            raise Exception(f"Erro ao enviar para SEFAZ: {str(e)}")
        
        # 6. Atualizar Status com base no retorno
        status_envio = resultado_envio.get('status')
        mensagem_envio = resultado_envio.get('mensagem') or ''

        if mensagem_envio:
            self.cte.observacoes_fiscais = mensagem_envio

        if status_envio == 'autorizado':
            self._processar_autorizacao(resultado_envio)
        elif status_envio == 'recebido':
            self.cte.status = 'REC'
            if resultado_envio.get('recibo'):
                self.cte.recibo = resultado_envio.get('recibo')
            self.cte.save(using=db_alias)

            recibo = self.cte.recibo
            if recibo:
                import time
                import logging
                logger = logging.getLogger(__name__)

                for i in range(5):
                    time.sleep(2)
                    try:
                        logger.info(f"Consultando recibo {recibo} (tentativa {i+1}/5)...")
                        retorno_consulta = self.gateway.consultar_recibo(recibo)

                        status_consulta = retorno_consulta.get('status')
                        mensagem_consulta = retorno_consulta.get('mensagem') or ''
                        if mensagem_consulta:
                            self.cte.observacoes_fiscais = mensagem_consulta

                        if retorno_consulta.get('recibo'):
                            self.cte.recibo = retorno_consulta.get('recibo')

                        if status_consulta == 'autorizado':
                            self._processar_autorizacao(retorno_consulta)
                            resultado_envio = retorno_consulta
                            break
                        elif status_consulta == 'rejeitado':
                            self.cte.status = 'REJ'
                            self.cte.save(using=db_alias)
                            resultado_envio = retorno_consulta
                            break
                        elif status_consulta == 'processando':
                            self.cte.status = 'PRO'
                            self.cte.save(using=db_alias)
                            continue
                        elif status_consulta == 'recebido':
                            self.cte.status = 'REC'
                            self.cte.save(using=db_alias)
                            continue
                        else:
                            logger.warning(f"Status desconhecido na consulta: {status_consulta}")
                            self.cte.save(using=db_alias)
                            continue

                    except Exception as e:
                        logger.error(f"Erro ao consultar recibo {recibo}: {e}")
                        continue

        elif status_envio == 'processando':
            self.cte.status = 'PRO'
            self.cte.save(using=db_alias)
        elif status_envio == 'rejeitado':
            self.cte.status = 'REJ'
            self.cte.save(using=db_alias)
        
        return resultado_envio

    def _processar_autorizacao(self, resultado):
         db_alias = self.slug or self.cte._state.db or 'default'
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
                self.cte.xml_cte = f'<cteProc xmlns="http://www.portalfiscal.inf.br/cte" versao="4.00">{xml_assinado_str}{xml_protocolo}</cteProc>'
         
         self.cte.save(using=db_alias)
