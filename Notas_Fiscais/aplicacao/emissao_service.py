from django.db import transaction
import logging

from ..models import Nota, NotaItemImposto
from ..dominio.builder import NotaBuilder
from ..infrastructure.certificado_loader import CertificadoLoader
from ..infrastructure.sefaz_adapter import SefazAdapter
from ..services.calculo_impostos_service import CalculoImpostosService
from .construir_nfe_pynfe import construir_nfe_pynfe
from core.excecoes import ErroDominio
from core.dominio_handler import tratar_erro, tratar_sucesso


logger = logging.getLogger(__name__)


class EmissaoService:

    def __init__(self, slug, database):
        self.slug = slug
        self.db = database

    def emitir(self, nota_id):
        nota = Nota.objects.using(self.db).get(id=nota_id)

        # 1) Calcular impostos item a item
        CalculoImpostosService(self.db).aplicar_impostos(nota)

        # 2) Montar DTO
        dto = NotaBuilder(nota, database=self.db).build()

        # 3) Montar objeto NFe (PyNFe)
        nfe_obj = construir_nfe_pynfe(dto)

        # 4) Certificado
        from Licencas.models import Filiais
        filial_obj = Filiais.objects.using(self.db).get(empr_empr=nota.empresa, empr_codi=nota.filial)

        try:
            cert_path, cert_pass = CertificadoLoader(filial_obj).load()
            logger.info(f"Certificado carregado com sucesso para empresa={nota.empresa}, filial={nota.filial}, caminho={cert_path}, senha={cert_pass}, tamanho={len(filial_obj.empr_cert_digi)} bytes")
        except Exception as e:
            detalhes = {
                "empresa": nota.empresa,
                "filial": nota.filial,
                "erro_original": str(e),
            }
            logger.error(
                "Falha ao carregar certificado digital A1 para empresa=%s filial=%s: %s",
                nota.empresa,
                nota.filial,
                e,
            )
            raise ErroDominio(
                "Certificado digital A1 inválido ou não configurado para esta filial.",
                codigo="certificado_a1_invalido",
                detalhes=detalhes,
            )

        try:
            adapter = SefazAdapter(cert_path, cert_pass, dto.emitente.uf, dto.ambiente)
        except Exception as e:
            detalhes = {"erro_original": str(e)}
            logger.error(
                "Falha ao inicializar comunicação com SEFAZ para empresa=%s filial=%s: %s",
                nota.empresa,
                nota.filial,
                e,
            )
            raise ErroDominio(
                "Não foi possível inicializar a comunicação com a SEFAZ usando o certificado A1.",
                codigo="sefaz_adapter_certificado_erro",
                detalhes=detalhes,
            )

        try:
            resposta = adapter.emitir(nfe_obj)
        except Exception as e:
            detalhes = {"erro_original": str(e)}
            logger.error(
                "Erro ao emitir nota na SEFAZ para empresa=%s filial=%s nota_id=%s: %s",
                nota.empresa,
                nota.filial,
                nota.id,
                e,
            )
            raise ErroDominio(
                "Falha ao enviar a nota para a SEFAZ.",
                codigo="sefaz_envio_erro",
                detalhes=detalhes,
            )

        # Converter objeto Element XML para string antes de salvar e retornar
        if 'xml' in resposta and not isinstance(resposta['xml'], str):
             try:
                from lxml import etree
                resposta['xml'] = etree.tostring(resposta['xml'], encoding='unicode')
             except Exception:
                try:
                    import xml.etree.ElementTree as ET
                    resposta['xml'] = ET.tostring(resposta['xml'], encoding='unicode')
                except Exception:
                    resposta['xml'] = str(resposta['xml'])

        # 7) Persistir
        with transaction.atomic(using=self.db):
            nota.chave_acesso = resposta.get("chave")
            nota.protocolo_autorizacao = resposta.get("protocolo")
            nota.xml_assinado = resposta["xml"]
            nota.status = resposta.get("status", 0)
            
            # Persistir motivo/mensagem de erro
            motivo = resposta.get("motivo")
            if motivo:
                from ..utils.sefaz_messages import get_sefaz_message
                status_code = resposta.get("status")
                msg_amigavel = get_sefaz_message(status_code, motivo)
                if str(status_code) == '778':
                    # Tenta sugerir NCMs corretos da tabela TIPI
                    try:
                        from ..utils.ncm_validator import buscar_sugestoes_ncm
                        # Extrai o NCM do XML ou do item da nota (precisa pegar o primeiro item se possível)
                        # Como não temos fácil acesso ao item aqui, vamos tentar pegar do XML se disponível
                        # Mas o XML pode não ter sido gerado se falhou antes.
                        # Melhor: Vamos pegar o NCM do primeiro item da nota no banco.
                        primeiro_item = nota.itens.first()
                        ncm_usado = getattr(primeiro_item, 'ncm', '') if primeiro_item else ''
                        
                        sugestoes = buscar_sugestoes_ncm(ncm_usado)
                        if sugestoes:
                            # Monta a mensagem final com as sugestões
                            mensagens_sugestoes = [s['mensagem'] for s in sugestoes]
                            msg_amigavel += " " + " ".join(mensagens_sugestoes)
                        else:
                            msg_amigavel += " Verifique se o NCM no cadastro do produto está correto e ativo na SEFAZ."
                    except Exception as e:
                        msg_amigavel += " Verifique se o NCM no cadastro do produto está correto e ativo na SEFAZ."
                
                nota.motivo_status = msg_amigavel
            else:
                nota.motivo_status = None

            # Se autorizada e temos o protocolo, montamos o procNFe para o xml_autorizado
            if nota.status == 100 and resposta.get("xml_protocolo"):
                xml_assinado_str = nota.xml_assinado
                # Remove declaração XML se existir para não ficar duplicada ou inválida dentro do procNFe
                if xml_assinado_str and xml_assinado_str.strip().startswith('<?xml'):
                    idx = xml_assinado_str.find('>')
                    if idx != -1:
                        xml_assinado_str = xml_assinado_str[idx+1:].strip()
                
                nota.xml_autorizado = f'<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">{xml_assinado_str}{resposta["xml_protocolo"]}</nfeProc>'

            nota.save(using=self.db)

        return resposta
