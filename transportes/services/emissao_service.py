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
             self.cte.status = 'AUT'
             self.cte.protocolo = resultado_envio.get('protocolo')
             self.cte.save()
        elif resultado_envio.get('status') == 'recebido':
             self.cte.status = 'REC' # Recebido/Em processamento
             self.cte.save()
             # Aqui poderia agendar a consulta do recibo
        elif resultado_envio.get('status') == 'rejeitado':
             self.cte.status = 'REJ'
             # Salvar motivo da rejeição se houver campo
             # self.cte.motivo_rejeicao = resultado_envio.get('mensagem')
             self.cte.save()
        
        return resultado_envio
