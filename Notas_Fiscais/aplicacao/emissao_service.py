from django.db import transaction
import logging
import re

from ..models import Nota, NotaItemImposto
from ..dominio.builder import NotaBuilder
from ..infrastructure.certificado_loader import CertificadoLoader
from ..infrastructure.sefaz_adapter import SefazAdapter
from ..services.calculo_impostos_service import CalculoImpostosService
from ..services.evento_service import EventoService
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
        if getattr(dto.emitente, "cpf", None):
            try:
                serie_int = int(str(dto.serie or "0"))
            except Exception:
                serie_int = 0
            if not (920 <= serie_int <= 969):
                raise ErroDominio(
                    "Para Produtor Rural (CPF) use série entre 920 e 969.",
                    codigo="serie_produtor_rural_invalida",
                    detalhes={"serie": dto.serie},
                )

        # 3) Montar objeto NFe (PyNFe)
        nfe_obj = construir_nfe_pynfe(dto)

        # 4) Certificado
        from Licencas.models import Filiais
        filial_obj = Filiais.objects.using(self.db).defer('empr_cert_digi').get(empr_empr=nota.empresa, empr_codi=nota.filial)

        try:
            cert_path, cert_pass = CertificadoLoader(filial_obj).load()
            tamanho = 0
            try:
                if hasattr(filial_obj, 'empr_cert_digi') and filial_obj.empr_cert_digi:
                    tamanho = len(filial_obj.empr_cert_digi)
            except Exception:
                pass
            logger.info(f"Certificado carregado com sucesso para empresa={nota.empresa}, filial={nota.filial}, caminho={cert_path}, senha={cert_pass}, tamanho={tamanho} bytes")
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

        if str(getattr(nota, "modelo", "")) == "65":
            uf = str(dto.emitente.uf or "").strip().upper()
            tp_amb = int(dto.ambiente or 2)

            id_token = str(getattr(filial_obj, "empr_id_toke", "") or "").strip()
            csc = str(getattr(filial_obj, "empr_csn_toke", "") or "").strip()

            csc_source = "filial"
            if (not id_token or not csc) and uf == "PR" and tp_amb != 1:
                csc = "TBPHFPLCMUIB4K4CGY3SJW1RE8YWQWFQ4D56"
                id_token = "1"
                csc_source = "fallback_pr_homologacao"
            if not id_token or not csc:
                logger.info(
                    "NFC-e CSC/IDToken ausente empresa=%s filial=%s uf=%s tpAmb=%s id_token=%s csc_len=%s csc_tail=%s source=%s",
                    nota.empresa,
                    nota.filial,
                    uf,
                    tp_amb,
                    id_token or "",
                    len(csc or ""),
                    (csc or "")[-4:] if csc else "",
                    csc_source,
                )
                raise ErroDominio(
                    "Filial sem CSC/ID Token configurado para NFC-e (modelo 65).",
                    codigo="nfce_csc_nao_configurado",
                    detalhes={
                        "empresa": nota.empresa,
                        "filial": nota.filial,
                    },
                )
            logger.info(
                "NFC-e CSC/IDToken selecionado empresa=%s filial=%s uf=%s tpAmb=%s id_token=%s csc_len=%s csc_tail=%s source=%s",
                nota.empresa,
                nota.filial,
                uf,
                tp_amb,
                id_token,
                len(csc),
                csc[-4:],
                csc_source,
            )
            print(
                f"DEBUG: NFC-e CSC/IDToken selecionado empresa={nota.empresa} filial={nota.filial} uf={uf} tpAmb={tp_amb} "
                f"id_token={id_token} csc_len={len(csc)} csc_tail={csc[-4:]} source={csc_source}"
            )
            nfe_obj._nfce_csc = {
                "id_token": id_token,
                "csc": csc,
                "uf": uf,
                "ambiente": str(tp_amb),
            }

        try:
            resposta = adapter.emitir(nfe_obj)
        except Exception as e:
            detalhes = {
                "erro_original": str(e),
                "erro_tipo": e.__class__.__name__,
                "erro_repr": repr(e),
            }
            logger.exception(
                "Erro ao emitir nota na SEFAZ para empresa=%s filial=%s nota_id=%s",
                nota.empresa,
                nota.filial,
                nota.id,
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

        # Tratamento para erro 539 (Duplicidade com diferença na Chave)
        if resposta.get("status") == 539:
            motivo = resposta.get("motivo", "")
            # Tenta extrair a chave original da mensagem de erro
            # Padrão comum: [chNFe:0000...]
            match = re.search(r"chNFe:?\s?(\d{44})", motivo)
            if match:
                chave_original = match.group(1)
                logger.info(f"Erro 539 detectado. Tentando recuperar nota pela chave original: {chave_original}")
                
                try:
                    consulta = adapter.consultar(chave_original)
                    if consulta.get("status") == 100:
                        logger.info("Consulta bem sucedida. Nota autorizada na SEFAZ. Atualizando localmente.")
                        resposta["status"] = 100
                        resposta["motivo"] = "Autorizado o uso da NF-e (Recuperado de Duplicidade)"
                        resposta["protocolo"] = consulta.get("protocolo")
                        resposta["xml_protocolo"] = consulta.get("xml_protocolo")
                        resposta["chave"] = chave_original
                        # Se possível, recuperar o XML original autorizado seria ideal, 
                        # mas a consulta retorna o protocolo e status. 
                        # O XML assinado original pode ser diferente do que tentamos enviar agora.
                        # Mas mantemos o XML que tentamos enviar ou usamos o da consulta se vier completo?
                        # O metodo consultar retorna xml_protocolo que é o protNFe.
                        # Precisamos do nfeProc completo? 
                        # Geralmente a consulta retorna apenas o status e protocolo.
                        # Vamos manter o XML gerado (que gerou duplicidade) mas atualizar a chave?
                        # NÃO! Se deu duplicidade com diferença na chave, o XML que temos É DIFERENTE do que está na SEFAZ.
                        # Deveríamos tentar baixar o XML da SEFAZ, mas a consulta pública não retorna o XML completo da nota.
                        # Solução paliativa: Salvar com a chave correta e protocolo. O XML armazenado pode ficar inconsistente com a assinatura.
                        # O ideal seria fazer download, mas precisa de manifesto.
                        # Vamos apenas atualizar chave e protocolo para permitir faturamento.
                except Exception as e_cons:
                    logger.error(f"Erro ao consultar chave original na duplicidade: {e_cons}")

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
            
            # Registrar Evento
            EventoService.registrar(
                nota=nota,
                tipo="autorizacao" if nota.status == 100 else "erro_emissao",
                descricao=nota.motivo_status or motivo or "Tentativa de emissão",
                xml=nota.xml_autorizado if nota.status == 100 else nota.xml_assinado,
                protocolo=nota.protocolo_autorizacao,
                using=self.db
            )

        return resposta

    def consultar_status(self, nota_id):
        nota = Nota.objects.using(self.db).get(id=nota_id)
        chave_consulta = nota.chave_acesso

        if not chave_consulta:
            # 1. Tenta no motivo_status da própria nota (Alta prioridade: se for erro de duplicidade, a chave real está aqui)
            if not chave_consulta and nota.motivo_status:
                match = re.search(r"(\d{44})", nota.motivo_status)
                if match:
                    chave_consulta = match.group(1)
                    print(f"=== CHAVE RECUPERADA DE MOTIVO_STATUS: {chave_consulta} ===")
                    logger.info(f"Recuperada chave {chave_consulta} do motivo_status da nota.")

            # 2. Tenta recuperar chave de evento de erro anterior (539 ou outros com chNFe)
            if not chave_consulta:
                from ..models import NotaEvento
                eventos_erro = NotaEvento.objects.using(self.db).filter(
                    nota=nota, 
                    descricao__contains="chNFe"
                ).order_by("-id")
                
                for ev in eventos_erro:
                    # Tenta capturar qualquer sequência de 44 dígitos na descrição
                    match = re.search(r"(\d{44})", ev.descricao or "")
                    
                    # Se não achou na descrição, tenta no XML do evento se existir
                    if not match and ev.xml:
                        match = re.search(r'(?:Id="NFe|chNFe>|chave:?\s?)(\d{44})', ev.xml)

                    if match:
                        chave_consulta = match.group(1)
                        print(f"=== CHAVE RECUPERADA DE EVENTO {ev.id}: {chave_consulta} ===")
                        logger.info(f"Recuperada chave {chave_consulta} do histórico de erros (Evento {ev.id}) para consulta.")
                        break
            
            # 3. Tenta extrair do XML armazenado na própria nota
            # Prioriza XML Autorizado (se existir, é a chave correta)
            # XML Assinado é a última opção (pode conter chave que gerou erro de duplicidade)
            if not chave_consulta:
                for xml_field in [nota.xml_autorizado, nota.xml_assinado]:
                    if xml_field:
                        # Procura por Id="NFe..." (atributo) ou <chNFe>...</chNFe> (tag)
                        match = re.search(r'(?:Id="NFe|chNFe>|chave:?\s?)(\d{44})', xml_field)
                        if match:
                            chave_consulta = match.group(1)
                            print(f"=== CHAVE RECUPERADA DE XML DA NOTA: {chave_consulta} ===")
                            logger.info(f"Recuperada chave {chave_consulta} do XML armazenado na nota.")
                            break

        if not chave_consulta:
            print("=== NENHUMA CHAVE DE 44 DÍGITOS ENCONTRADA PARA CONSULTA ===")
            # Tenta gerar a chave se tivermos os dados (não recomendado aqui pois pode gerar chave diferente da que deu erro)
            # Mas podemos tentar ver se a chave já foi gerada e salva em algum lugar? Não.
            raise ErroDominio("Nota não possui chave de acesso e não foi possível recuperá-la do histórico para consulta.")

        from Licencas.models import Filiais
        filial_obj = Filiais.objects.using(self.db).defer('empr_cert_digi').get(empr_empr=nota.empresa, empr_codi=nota.filial)

        try:
            cert_path, cert_pass = CertificadoLoader(filial_obj).load()
        except Exception as e:
            detalhes = {
                "empresa": nota.empresa,
                "filial": nota.filial,
                "erro_original": str(e),
            }
            logger.error(
                "Falha ao carregar certificado para consulta: %s", e
            )
            raise ErroDominio(
                "Certificado digital inválido.",
                codigo="certificado_invalido",
                detalhes=detalhes,
            )

        try:
            ambiente = int(filial_obj.empr_ambi_nfe or 2)
            uf = filial_obj.empr_esta
            adapter = SefazAdapter(cert_path, cert_pass, uf, ambiente)
            
            resposta = adapter.consultar(chave_consulta)
            
            status_sefaz = resposta.get("status")
            motivo_sefaz = resposta.get("motivo")
            protocolo_sefaz = resposta.get("protocolo")
            xml_prot_sefaz = resposta.get("xml_protocolo")

            # Tratamento de Duplicidade (539/204) com Chave Diferente na Consulta
            # Se consultamos uma chave e a SEFAZ diz que é duplicata de OUTRA, usamos a outra.
            if str(status_sefaz) in ["539", "204"] and motivo_sefaz:
                 # Tenta extrair a chave correta do motivo
                 # Padrão esperado: "Duplicidade... [CHAVE]"
                 match = re.search(r"\[(\d{44})\]", motivo_sefaz)
                 if match:
                     chave_correta = match.group(1)
                     # Só faz sentido se a chave retornada for diferente da que usamos
                     if chave_correta != chave_consulta:
                         print(f"=== DUPLICIDADE DETECTADA NA CONSULTA. Chave correta na SEFAZ: {chave_correta} ===")
                         logger.info(f"Corrigindo chave de acesso de {chave_consulta} para {chave_correta} devido a duplicidade na SEFAZ.")
                         
                         # Atualiza a chave localmente para a correta e refaz a consulta IMEDIATAMENTE
                         chave_consulta = chave_correta
                         
                         # Refaz a consulta com a chave correta para pegar o protocolo e status 100
                         resposta = adapter.consultar(chave_consulta)
                         
                         # Atualiza as variáveis com o resultado da nova consulta
                         status_sefaz = resposta.get("status")
                         motivo_sefaz = resposta.get("motivo")
                         protocolo_sefaz = resposta.get("protocolo")
                         xml_prot_sefaz = resposta.get("xml_protocolo")

            with transaction.atomic(using=self.db):
                # Se achamos a chave (seja na nota ou recuperada), salvamos ela
                if chave_consulta and nota.chave_acesso != chave_consulta:
                    nota.chave_acesso = chave_consulta

                # Status de Sucesso (Autorizada) ou Cancelada/Denegada que são estados finais válidos
                if status_sefaz in [100, 101, 110, 301, 302]:
                    nota.status = status_sefaz
                    nota.protocolo_autorizacao = protocolo_sefaz
                    nota.motivo_status = motivo_sefaz
                    
                    # Se for autorizada (100) ou denegada/cancelada com protocolo, tenta montar o procNFe
                    if xml_prot_sefaz and nota.xml_assinado:
                        xml_assinado_str = nota.xml_assinado
                        # Remove declaração XML se existir para não ficar duplicada ou inválida dentro do procNFe
                        if xml_assinado_str and xml_assinado_str.strip().startswith('<?xml'):
                            idx = xml_assinado_str.find('>')
                            if idx != -1:
                                xml_assinado_str = xml_assinado_str[idx+1:].strip()
                        
                        nota.xml_autorizado = f'<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">{xml_assinado_str}{xml_prot_sefaz}</nfeProc>'
                    
                    nota.save(using=self.db)
                else:
                     # Outros status (ex: 217 - Não consta na base, ou erro temporário)
                     # Apenas atualizamos o motivo para o usuário saber o que houve
                     nota.motivo_status = motivo_sefaz
                     nota.save(using=self.db, update_fields=["motivo_status", "chave_acesso"])

            return resposta

        except Exception as e:
            logger.error(f"Erro ao consultar status na SEFAZ: {e}")
            raise ErroDominio(f"Erro ao consultar status: {str(e)}")

    def cancelar_nota(self, nota_id, justificativa):
        nota = Nota.objects.using(self.db).get(id=nota_id)
        
        # Validar status atual
        # 100 = Autorizada
        # 205 = Denegada (não pode cancelar)
        # 101 = Cancelada (já está)
        if nota.status == 101:
            raise ErroDominio("Nota já está cancelada.")
            
        if nota.status != 100:
            raise ErroDominio(f"A nota não pode ser cancelada pois está com status {nota.status}. Apenas notas autorizadas (100) podem ser canceladas.")

        if not nota.chave_acesso or not nota.protocolo_autorizacao:
            raise ErroDominio("Nota não possui chave de acesso ou protocolo de autorização, impossível cancelar.")
            
        from Licencas.models import Filiais
        filial_obj = Filiais.objects.using(self.db).defer('empr_cert_digi').get(empr_empr=nota.empresa, empr_codi=nota.filial)

        try:
            cert_path, cert_pass = CertificadoLoader(filial_obj).load()
        except Exception as e:
            raise ErroDominio("Falha ao carregar certificado digital.", detalhes={"erro": str(e)})

        try:
            ambiente = int(filial_obj.empr_ambi_nfe or 2)
            uf = filial_obj.empr_esta
            adapter = SefazAdapter(cert_path, cert_pass, uf, ambiente)
            
            # Precisamos do CNPJ da filial
            cnpj = filial_obj.empr_docu
            # Limpar CNPJ de formatação
            cnpj = re.sub(r"\D", "", str(cnpj))
            
            resultado = adapter.cancelar(
                chave=nota.chave_acesso,
                protocolo=nota.protocolo_autorizacao,
                justificativa=justificativa,
                cnpj=cnpj
            )
            
            # Verificar sucesso 
            # 135: Evento registrado e vinculado a NF-e
            # 136: Evento registrado, mas não vinculado a NF-e
            # 155: Cancelamento homologado fora de prazo
            status_canc = resultado.get("status")
            motivo_canc = resultado.get("motivo")
            protocolo_canc = resultado.get("protocolo")
            xml_envio = resultado.get("xml_envio")
            xml_retorno = resultado.get("xml_retorno")
            
            if status_canc in [135, 136, 155]: 
                 # Atualizar banco local
                 from ..services.nota_service import NotaService
                 NotaService.cancelar(
                     nota=nota, 
                     descricao=justificativa,
                     xml=xml_retorno,
                     protocolo=protocolo_canc,
                     database=self.db
                 )
                 
                 logger.info(f"Nota {nota.id} cancelada com sucesso na SEFAZ. Protocolo: {protocolo_canc}")
                 return resultado
            else:
                 # Erro no cancelamento
                 logger.error(f"Falha ao cancelar nota {nota.id} na SEFAZ: {status_canc} - {motivo_canc}")
                 
                 # Registrar tentativa de evento de erro
                 EventoService.registrar(
                    nota=nota,
                    tipo="erro_cancelamento",
                    descricao=f"Falha ao cancelar: {motivo_canc} (Cód: {status_canc})",
                    xml=xml_retorno or xml_envio,
                    using=self.db
                 )
                 
                 # Retorna o erro da SEFAZ
                 raise ErroDominio(f"Falha ao cancelar na SEFAZ: {motivo_canc}", codigo="sefaz_cancelamento_erro")

        except Exception as e:
            if isinstance(e, ErroDominio):
                raise e
            raise ErroDominio(f"Erro inesperado ao cancelar nota: {str(e)}")
