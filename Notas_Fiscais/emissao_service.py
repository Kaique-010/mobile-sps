"""
Serviço de emissão de notas fiscais usando PyNFe
"""
import logging
from datetime import datetime
from decimal import Decimal
from django.conf import settings
from pynfe.processamento.comunicacao import ComunicacaoSefaz
from pynfe.entidades.cliente import Cliente
from pynfe.entidades.emitente import Emitente
from pynfe.entidades.notafiscal import NotaFiscal as NFePyNFe
from pynfe.entidades.fonte_dados import _fonte_dados_nfe
from pynfe.utils.flags import CODIGO_BRASIL

logger = logging.getLogger(__name__)


class EmissaoNFeService:
    """Serviço para emissão de NFe usando PyNFe"""
    
    def __init__(self, certificado_path, senha_certificado, uf='PR', homologacao=True):
        self.certificado_path = certificado_path
        self.senha_certificado = senha_certificado
        self.uf = uf.lower()
        self.homologacao = homologacao
        self.comunicacao = None
        
    def _inicializar_comunicacao(self):
        """Inicializa comunicação com SEFAZ"""
        if not self.comunicacao:
            self.comunicacao = ComunicacaoSefaz(
                self.uf,
                self.certificado_path,
                self.senha_certificado,
                self.homologacao
            )
        return self.comunicacao
    
    def verificar_status_servico(self):
        """Verifica status do serviço da SEFAZ"""
        try:
            com = self._inicializar_comunicacao()
            response = com.status_servico('nfe')
            logger.info(f"Status do serviço SEFAZ: {response.text}")
            return response
        except Exception as e:
            logger.error(f"Erro ao verificar status do serviço: {e}")
            raise
    
    def criar_emitente(self, dados_emitente):
        """Cria objeto emitente para PyNFe"""
        emitente = Emitente(
            razao_social=dados_emitente['razao_social'],
            nome_fantasia=dados_emitente.get('nome_fantasia', ''),
            cnpj=dados_emitente['cnpj'],
            codigo_de_regime_tributario=dados_emitente.get('regime_tributario', '1'),
            inscricao_estadual=dados_emitente['inscricao_estadual'],
            inscricao_municipal=dados_emitente.get('inscricao_municipal', ''),
            cnae_fiscal=dados_emitente.get('cnae_fiscal', ''),
            endereco_logradouro=dados_emitente['logradouro'],
            endereco_numero=dados_emitente['numero'],
            endereco_complemento=dados_emitente.get('complemento', ''),
            endereco_bairro=dados_emitente['bairro'],
            endereco_municipio=dados_emitente['municipio'],
            endereco_uf=dados_emitente['uf'],
            endereco_cep=dados_emitente['cep'],
            endereco_pais=CODIGO_BRASIL,
            telefone=dados_emitente.get('telefone', ''),
            email=dados_emitente.get('email', '')
        )
        return emitente
    
    def criar_cliente(self, dados_cliente):
        """Cria objeto cliente/destinatário para PyNFe"""
        cliente = Cliente(
            razao_social=dados_cliente['razao_social'],
            tipo_documento='CNPJ' if dados_cliente.get('cnpj') else 'CPF',
            email=dados_cliente.get('email', ''),
            numero_documento=dados_cliente.get('cnpj') or dados_cliente.get('cpf'),
            inscricao_estadual=dados_cliente.get('inscricao_estadual', ''),
            endereco_logradouro=dados_cliente['logradouro'],
            endereco_numero=dados_cliente['numero'],
            endereco_complemento=dados_cliente.get('complemento', ''),
            endereco_bairro=dados_cliente['bairro'],
            endereco_municipio=dados_cliente['municipio'],
            endereco_uf=dados_cliente['uf'],
            endereco_cep=dados_cliente['cep'],
            endereco_pais=CODIGO_BRASIL,
            telefone=dados_cliente.get('telefone', '')
        )
        return cliente
    
    def criar_nfe(self, dados_nfe, emitente, cliente, itens):
        """Cria objeto NFe para emissão"""
        try:
            # Criar nota fiscal
            nfe = NFePyNFe(
                emitente=emitente,
                cliente=cliente,
                uf=self.uf.upper(),
                natureza_operacao=dados_nfe['natureza_operacao'],
                forma_pagamento=dados_nfe.get('forma_pagamento', 0),
                tipo_pagamento=dados_nfe.get('tipo_pagamento', 1),
                modelo=dados_nfe.get('modelo', 55),
                serie=dados_nfe.get('serie', 1),
                numero_nf=dados_nfe['numero'],
                data_emissao=dados_nfe.get('data_emissao', datetime.now()),
                data_saida_entrada=dados_nfe.get('data_saida_entrada', datetime.now()),
                tipo_documento=dados_nfe.get('tipo_documento', 1),  # 1=Saída
                municipio=dados_nfe.get('municipio_ocorrencia'),
                tipo_impressao_danfe=dados_nfe.get('tipo_impressao_danfe', 1),
                forma_emissao=dados_nfe.get('forma_emissao', 1),
                cliente_final=dados_nfe.get('cliente_final', 1),
                indicador_destino=dados_nfe.get('indicador_destino', 1),
                indicador_presenca=dados_nfe.get('indicador_presenca', 1),
                finalidade_emissao=dados_nfe.get('finalidade_emissao', 1),
                processo_emissao=dados_nfe.get('processo_emissao', 0),
                transporte_modalidade_frete=dados_nfe.get('modalidade_frete', 9)
            )
            
            # Adicionar itens
            for item_data in itens:
                nfe.adicionar_produto_servico(
                    codigo=item_data['codigo'],
                    descricao=item_data['descricao'],
                    ncm=item_data.get('ncm', ''),
                    cfop=item_data['cfop'],
                    unidade_comercial=item_data.get('unidade', 'UN'),
                    quantidade_comercial=Decimal(str(item_data['quantidade'])),
                    valor_unitario_comercial=Decimal(str(item_data['valor_unitario'])),
                    valor_total_bruto=Decimal(str(item_data['valor_total'])),
                    unidade_tributavel=item_data.get('unidade', 'UN'),
                    quantidade_tributavel=Decimal(str(item_data['quantidade'])),
                    valor_unitario_tributavel=Decimal(str(item_data['valor_unitario'])),
                    origem_mercadoria=item_data.get('origem', 0),
                    modalidade_icms=item_data.get('modalidade_icms', 102),
                    valor_icms=Decimal(str(item_data.get('valor_icms', 0))),
                    valor_ipi=Decimal(str(item_data.get('valor_ipi', 0))),
                    valor_pis=Decimal(str(item_data.get('valor_pis', 0))),
                    valor_cofins=Decimal(str(item_data.get('valor_cofins', 0)))
                )
            
            return nfe
            
        except Exception as e:
            logger.error(f"Erro ao criar NFe: {e}")
            raise
    
    def emitir_nfe(self, dados_nfe, dados_emitente, dados_cliente, itens):
        """Emite uma NFe completa"""
        try:
            logger.info(f"Iniciando emissão da NFe número: {dados_nfe['numero']}")
            
            # Verificar status do serviço
            self.verificar_status_servico()
            
            # Criar objetos
            emitente = self.criar_emitente(dados_emitente)
            cliente = self.criar_cliente(dados_cliente)
            nfe = self.criar_nfe(dados_nfe, emitente, cliente, itens)
            
            # Processar NFe
            com = self._inicializar_comunicacao()
            
            # Assinar e enviar
            processo_nfe = com.autorizar('nfe', nfe)
            
            if processo_nfe.resposta.cStat == '100':  # Autorizada
                logger.info(f"NFe {dados_nfe['numero']} autorizada com sucesso")
                return {
                    'sucesso': True,
                    'chave_acesso': processo_nfe.resposta.chNFe,
                    'protocolo': processo_nfe.resposta.nProt,
                    'xml_autorizado': processo_nfe.resposta.xml,
                    'data_autorizacao': processo_nfe.resposta.dhRecbto,
                    'status': processo_nfe.resposta.cStat,
                    'motivo': processo_nfe.resposta.xMotivo
                }
            else:
                logger.error(f"Erro na autorização da NFe: {processo_nfe.resposta.xMotivo}")
                return {
                    'sucesso': False,
                    'status': processo_nfe.resposta.cStat,
                    'motivo': processo_nfe.resposta.xMotivo,
                    'xml_envio': processo_nfe.xml
                }
                
        except Exception as e:
            logger.error(f"Erro ao emitir NFe: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def consultar_nfe(self, chave_acesso):
        """Consulta situação de uma NFe pela chave de acesso"""
        try:
            com = self._inicializar_comunicacao()
            resposta = com.consultar_nfe(chave_acesso)
            
            return {
                'chave_acesso': chave_acesso,
                'status': resposta.cStat,
                'motivo': resposta.xMotivo,
                'protocolo': getattr(resposta, 'nProt', None),
                'data_autorizacao': getattr(resposta, 'dhRecbto', None)
            }
            
        except Exception as e:
            logger.error(f"Erro ao consultar NFe {chave_acesso}: {e}")
            raise
    
    def cancelar_nfe(self, chave_acesso, protocolo, justificativa):
        """Cancela uma NFe autorizada"""
        try:
            com = self._inicializar_comunicacao()
            resposta = com.cancelar_nfe(
                chave_acesso=chave_acesso,
                protocolo=protocolo,
                justificativa=justificativa
            )
            
            if resposta.cStat == '135':  # Cancelamento autorizado
                return {
                    'sucesso': True,
                    'protocolo_cancelamento': resposta.nProt,
                    'data_cancelamento': resposta.dhRecbto
                }
            else:
                return {
                    'sucesso': False,
                    'status': resposta.cStat,
                    'motivo': resposta.xMotivo
                }
                
        except Exception as e:
            logger.error(f"Erro ao cancelar NFe {chave_acesso}: {e}")
            raise