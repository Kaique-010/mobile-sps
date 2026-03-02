from pynfe.processamento.comunicacao import ComunicacaoSefaz
from pynfe.processamento.assinatura import AssinaturaA1
from pynfe.processamento.serializacao import SerializacaoXML
from pynfe.entidades.fonte_dados import _fonte_dados
from lxml import etree
import base64
import hashlib

class SefazAdapter:

    def __init__(self, cert_path, cert_pass, uf, ambiente):
        self.uf = uf
        self.ambiente = ambiente
        self.cert_path = cert_path
        self.cert_pass = cert_pass
        self.assinador = AssinaturaA1(cert_path, cert_pass)
        self.homologacao = True if int(ambiente) == 2 else False
        self.comunicacao = ComunicacaoSefaz(uf, cert_path, cert_pass, self.homologacao)

    def emitir(self, nota_fiscal):
        serializador = SerializacaoXML(_fonte_dados, homologacao=self.homologacao)
        nfe = serializador.exportar(nota_fiscal)
        
        # Injeta IBS e CBS se disponíveis (contornando limitação do PyNFe)
        if hasattr(nota_fiscal, '_itens_extra'):
            self._injetar_ibs_cbs(nfe, nota_fiscal._itens_extra)

        # Injeta Responsável Técnico se disponível (necessário para evitar Rejeição 972/225)
        if hasattr(nota_fiscal, '_responsavel_tecnico'):
            self._injetar_responsavel_tecnico(nfe, nota_fiscal._responsavel_tecnico)
            
        xml_assinado = self.assinador.assinar(nfe)

        # Determina se é NF-e ou NFC-e para escolher o endpoint correto
        modelo_envio = 'nfe'
        if hasattr(nota_fiscal, 'modelo') and str(nota_fiscal.modelo) == '65':
            modelo_envio = 'nfce'
            
        envio = self.comunicacao.autorizacao(modelo=modelo_envio, nota_fiscal=xml_assinado)
        
        status = None
        motivo = None
        protocolo = None
        chave = None
        xml_protocolo = None

        try:
            # envio[0] é o status retornado pelo PyNFe (pode ser 1 para sucesso, mas precisamos do cStat da SEFAZ)
            # envio[1] é o objeto response do requests
            resposta = envio[1]

            # DEBUG EXPLICITO PARA O TERMINAL (SOLICITADO PELO USUARIO)
            if resposta and hasattr(resposta, 'text'):
                print("\n\n" + "="*50)
                print(f"=== SEFAZ ADAPTER RESPONSE (DEBUG TERMINAL) ===")
                print(f"STATUS HTTP: {getattr(resposta, 'status_code', 'N/A')}")
                print(f"CONTENT:\n{resposta.text}")
                print("="*50 + "\n\n")
            
            # Tenta extrair informações do XML de retorno da SEFAZ
            if resposta and hasattr(resposta, 'content'):
                try:
                    from lxml import etree
                    root = etree.fromstring(resposta.content)
                    ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
                    
                    # Procura por protNFe (Protocolo de Autorização)
                    prot_nfe = root.find('.//ns:protNFe', namespaces=ns)
                    if prot_nfe is not None:
                        # Extrai o XML do protocolo para montar o procNFe posteriormente
                        xml_protocolo = etree.tostring(prot_nfe, encoding='unicode')

                        inf_prot = prot_nfe.find('.//ns:infProt', namespaces=ns)
                        if inf_prot is not None:
                            # cStat
                            c_stat_elem = inf_prot.find('.//ns:cStat', namespaces=ns)
                            if c_stat_elem is not None:
                                status = int(c_stat_elem.text)
                            
                            # nProt
                            n_prot_elem = inf_prot.find('.//ns:nProt', namespaces=ns)
                            if n_prot_elem is not None:
                                protocolo = n_prot_elem.text
                                
                            # xMotivo
                            x_motivo_elem = inf_prot.find('.//ns:xMotivo', namespaces=ns)
                            if x_motivo_elem is not None:
                                motivo = x_motivo_elem.text
                            
                            # chNFe
                            ch_nfe_elem = inf_prot.find('.//ns:chNFe', namespaces=ns)
                            if ch_nfe_elem is not None:
                                chave = ch_nfe_elem.text

                    # Se não achou protNFe, pode ser rejeição no nível do lote ou processamento
                    if status is None:
                        c_stat_elem = root.find('.//ns:cStat', namespaces=ns)
                        if c_stat_elem is not None:
                            status = int(c_stat_elem.text)
                        
                        x_motivo_elem = root.find('.//ns:xMotivo', namespaces=ns)
                        if x_motivo_elem is not None:
                            motivo = x_motivo_elem.text

                except Exception as e_parse:
                    # Fallback se falhar o parser XML
                    motivo = f"Erro ao parsear XML SEFAZ: {str(e_parse)}"
            
            # Fallback se status ainda for None, usa o do PyNFe ou assume erro
            if status is None:
                status = envio[0]
                motivo = getattr(resposta, 'text', str(resposta))

        except Exception as e:
            motivo = str(e)
            status = None

        return {
            "xml": xml_assinado,
            "codigo": None,
            "motivo": motivo,
            "status": status,
            "protocolo": protocolo,
            "chave": chave,
            "xml_protocolo": xml_protocolo,
        }

    def consultar(self, chave):
        """
        Consulta o status de uma nota na SEFAZ pela chave de acesso.
        """
        try:
            # Determina o modelo pela chave de acesso (posições 20-21, base 0)
            # Se for 65, é NFC-e. Se for 55, é NF-e.
            modelo_envio = 'nfe'
            if len(chave) == 44:
                mod = chave[20:22]
                if mod == '65':
                    modelo_envio = 'nfce'

            # Consulta pela chave
            print(f"\n=== CONSULTANDO CHAVE: {chave} (Modelo: {modelo_envio}) ===")
            resposta = self.comunicacao.consulta_nota(modelo=modelo_envio, chave=chave)
            
            # O retorno de consulta_nota é diretamente o objeto Response do requests (ou similar)
            # Não é uma tupla (status, response) como em outros métodos
            
            # DEBUG EXPLICITO
            if resposta and hasattr(resposta, 'text'):
                print(f"=== RETORNO CONSULTA SEFAZ ===\n{resposta.text}\n==============================\n")

            status = None
            motivo = None
            protocolo = None
            xml_protocolo = None
            
            if resposta and hasattr(resposta, 'content'):
                from lxml import etree
                try:
                    root = etree.fromstring(resposta.content)
                    ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
                    
                    # Procura por protNFe (Protocolo de Autorização)
                    # Na consulta, o retorno é um retConsSitNFe que contém o protNFe
                    prot_nfe = root.find('.//ns:protNFe', namespaces=ns)
                    
                    if prot_nfe is not None:
                        xml_protocolo = etree.tostring(prot_nfe, encoding='unicode')
                        
                        inf_prot = prot_nfe.find('.//ns:infProt', namespaces=ns)
                        if inf_prot is not None:
                            c_stat_elem = inf_prot.find('.//ns:cStat', namespaces=ns)
                            if c_stat_elem is not None:
                                status = int(c_stat_elem.text)
                            
                            n_prot_elem = inf_prot.find('.//ns:nProt', namespaces=ns)
                            if n_prot_elem is not None:
                                protocolo = n_prot_elem.text
                                
                            x_motivo_elem = inf_prot.find('.//ns:xMotivo', namespaces=ns)
                            if x_motivo_elem is not None:
                                motivo = x_motivo_elem.text
                    
                    # Se não achou protNFe, verifica o status da consulta em si (cStat do retConsSitNFe)
                    if status is None:
                        c_stat_elem = root.find('.//ns:cStat', namespaces=ns)
                        if c_stat_elem is not None:
                            status = int(c_stat_elem.text)
                        
                        x_motivo_elem = root.find('.//ns:xMotivo', namespaces=ns)
                        if x_motivo_elem is not None:
                            motivo = x_motivo_elem.text

                except Exception as e:
                    motivo = f"Erro ao parsear XML de consulta: {str(e)}"
            
            return {
                "status": status,
                "motivo": motivo,
                "protocolo": protocolo,
                "xml_protocolo": xml_protocolo,
                "chave": chave
            }

        except Exception as e:
            return {
                "status": None,
                "motivo": f"Erro na consulta: {str(e)}",
                "protocolo": None,
                "xml_protocolo": None,
                "chave": chave
            }

    def cancelar(self, chave, protocolo, justificativa, cnpj):
        from pynfe.entidades.evento import Evento
        from pynfe.processamento.serializacao import SerializacaoXML
        from pynfe.entidades.fonte_dados import _fonte_dados
        from datetime import datetime

        print(f"\n=== CANCELANDO CHAVE: {chave} ===")
        
        # O método serializar_evento do PyNFe espera a SIGLA da UF no atributo 'uf'
        # e converte internamente para código IBGE.
        # Assume-se que self.uf já é a sigla (ex: 'PR', 'SP').
        # Se self.uf for numérico, precisamos converter para sigla ou ajustar a lógica.
        # Pela implementação do projeto, self.uf vem de Filiais.empr_esta que é sigla.
        
        # Gera ID do evento: ID + tpEvento + Chave + nSeqEvento (01)
        # NOTA: O PyNFe calcula a propriedade 'identificador' automaticamente baseada em tp_evento, chave e n_seq_evento.
        # Não devemos passar 'identificador' no construtor pois é uma property sem setter.
        tp_evento = '110111'
        n_seq_evento = 1
        
        # Cria o objeto Evento com os atributos esperados pelo serializar_evento
        evento = Evento(
            uf=self.uf, # Sigla
            cnpj=cnpj,
            chave=chave,
            data_emissao=datetime.now(),
            tp_evento=tp_evento,
            n_seq_evento=n_seq_evento,
            descricao='Cancelamento', # Obrigatório para ativar a lógica de cancelamento no serializador
            protocolo=str(protocolo),
            justificativa=justificativa,
            versao="1.00"
        )
        
        # Serializa
        try:
            serializador = SerializacaoXML(_fonte_dados, homologacao=self.homologacao)
            # O método exportar é hardcoded para NFe, precisamos usar serializar_evento para eventos
            xml_evento = serializador.serializar_evento(evento)
        except Exception as e_ser:
             # Log detalhado do erro
             import traceback
             traceback.print_exc()
             raise Exception(f"Erro na serialização do evento: {str(e_ser)} (Verifique logs para traceback)")
        
        # O método exportar retorna um objeto Element do lxml
        # O assinador espera um Element ou string XML
        
        # Assina
        # Se xml_evento for None, a serialização falhou
        if xml_evento is None:
             raise Exception(f"Falha na serialização do evento de cancelamento (xml_evento is None).")
             
        xml_assinado = self.assinador.assinar(xml_evento)
        
        # Envia
        # O método evento espera o XML assinado (Element)
        
        # Determina o modelo pela chave de acesso
        modelo_envio = 'nfe'
        if len(chave) == 44:
            mod = chave[20:22]
            if mod == '65':
                modelo_envio = 'nfce'

        resposta = self.comunicacao.evento(modelo=modelo_envio, evento=xml_assinado)
        
        return self._processar_resposta_evento(resposta, xml_assinado)

    def _processar_resposta_evento(self, resposta, xml_envio):
        status = None
        motivo = None
        protocolo = None
        xml_retorno = None
        
        try:
            # Tenta extrair XML da resposta
            if hasattr(resposta, 'content'):
                xml_retorno = resposta.content
            elif hasattr(resposta, 'text'):
                xml_retorno = resposta.text.encode('utf-8')
            else:
                xml_retorno = str(resposta).encode('utf-8')

            # Parse XML
            root = etree.fromstring(xml_retorno)
            ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
            
            # Procura retEvento
            # A estrutura geralmente é <retEnvEvento><retEvento><infEvento>...</infEvento></retEvento></retEnvEvento>
            ret_evento = root.find('.//ns:retEvento', namespaces=ns)
            
            if ret_evento is not None:
                inf_evento = ret_evento.find('.//ns:infEvento', namespaces=ns)
                if inf_evento is not None:
                    c_stat = inf_evento.find('.//ns:cStat', namespaces=ns)
                    if c_stat is not None:
                        status = int(c_stat.text)
                    
                    x_motivo = inf_evento.find('.//ns:xMotivo', namespaces=ns)
                    if x_motivo is not None:
                        motivo = x_motivo.text
                    
                    n_prot = inf_evento.find('.//ns:nProt', namespaces=ns)
                    if n_prot is not None:
                        protocolo = n_prot.text
            
            if status is None:
                # Tenta pegar cStat do nível superior se falhou (ex: erro de lote)
                c_stat = root.find('.//ns:cStat', namespaces=ns)
                if c_stat is not None:
                    status = int(c_stat.text)
                x_motivo = root.find('.//ns:xMotivo', namespaces=ns)
                if x_motivo is not None:
                    motivo = x_motivo.text

        except Exception as e:
            motivo = f"Erro ao processar resposta de cancelamento: {str(e)}"
            
        return {
            "status": status,
            "motivo": motivo,
            "protocolo": protocolo,
            "xml_envio": etree.tostring(xml_envio, encoding='unicode') if xml_envio is not None else None,
            "xml_retorno": xml_retorno.decode('utf-8') if xml_retorno else None
        }

    def _injetar_ibs_cbs(self, nfe_elem, itens_extra):
        # Namespace
        ns_uri = 'http://www.portalfiscal.inf.br/nfe'
        ns = {'ns': ns_uri}
        
        # Encontra os detalhes (itens)
        dets = nfe_elem.findall('.//ns:det', namespaces=ns)
        
        # Fallback: tentar sem namespace se não encontrar
        if not dets:
            dets = nfe_elem.findall('.//det')
            
        print(f"DEBUG: _injetar_ibs_cbs: Encontrados {len(dets)} dets e {len(itens_extra)} itens_extra")

        if len(dets) != len(itens_extra):
            print("DEBUG: _injetar_ibs_cbs: Contagem incompatível. Abortando injeção.")
            return

        for i, det in enumerate(dets):
            dados = itens_extra[i]
            
            # Tenta encontrar imposto com ou sem namespace
            imposto = det.find('.//ns:imposto', namespaces=ns)
            if imposto is None:
                imposto = det.find('.//imposto')
                
            if imposto is None: 
                print(f"DEBUG: Item {i} sem tag imposto.")
                continue
            
            def fmt(v): return "{:.2f}".format(float(v or 0))
            
            # Helper para criar elemento com namespace correto (se o pai tiver)
            def sub(parent, tag, text=None):
                # Se o pai tem namespace, tenta usar o mesmo
                if parent.tag.startswith('{'):
                    ns_prefix = parent.tag.split('}')[0] + '}'
                    elem = etree.SubElement(parent, f"{ns_prefix}{tag}")
                else:
                    elem = etree.SubElement(parent, tag)
                if text: elem.text = text
                return elem
            
            # IBS
            ibs_data = dados.get('ibs')
            if ibs_data:
                # Validar se tem valor antes de injetar (Evitar erro de Schema 225)
                # A SEFAZ pode rejeitar tags de imposto com valor 0.00
                valor_ibs = float(ibs_data.get('valor') or 0)
                if valor_ibs > 0:
                    ibs = sub(imposto, "IBS")
                    sub(ibs, "vBCIBS", fmt(ibs_data.get('base')))
                    sub(ibs, "pIBS", fmt(ibs_data.get('aliq')))
                    sub(ibs, "vIBS", fmt(ibs_data.get('valor')))
                else:
                    print(f"DEBUG: IBS zerado ({valor_ibs}), ignorando injeção para evitar erro 225.")
            
            # CBS
            cbs_data = dados.get('cbs')
            if cbs_data:
                # Validar se tem valor antes de injetar
                valor_cbs = float(cbs_data.get('valor') or 0)
                if valor_cbs > 0:
                    cbs = sub(imposto, "CBS")
                    sub(cbs, "vBCCBS", fmt(cbs_data.get('base')))
                    sub(cbs, "pCBS", fmt(cbs_data.get('aliq')))
                    sub(cbs, "vCBS", fmt(cbs_data.get('valor')))
                else:
                    print(f"DEBUG: CBS zerado ({valor_cbs}), ignorando injeção para evitar erro 225.")
            
            print(f"DEBUG: Injetado IBS/CBS no item {i}")

    def _injetar_responsavel_tecnico(self, nfe_elem, resp_dto):
        # Helper para criar elemento com namespace correto
        def sub(parent, tag, text=None):
            if parent.tag.startswith('{'):
                ns_prefix = parent.tag.split('}')[0] + '}'
                elem = etree.SubElement(parent, f"{ns_prefix}{tag}")
            else:
                elem = etree.SubElement(parent, tag)
            if text: elem.text = str(text)
            return elem

        ns_uri = 'http://www.portalfiscal.inf.br/nfe'
        ns = {'ns': ns_uri}
        
        # Encontra infNFe
        inf_nfe = nfe_elem.find('.//ns:infNFe', namespaces=ns)
        if inf_nfe is None:
            inf_nfe = nfe_elem.find('.//infNFe')
            
        if inf_nfe is None:
            print("DEBUG: _injetar_responsavel_tecnico: infNFe não encontrado.")
            return

        print(f"DEBUG: Injetando infRespTec para CNPJ {resp_dto.cnpj}")

        # Calcula o hashCSRT se tivermos a chave CSRT e o ID da nota
        if resp_dto.csrt_key and not resp_dto.hash_csrt:
            nfe_id = inf_nfe.get("Id")
            if nfe_id and nfe_id.startswith("NFe"):
                chave_acesso = nfe_id[3:] # Remove o prefixo NFe
                
                # Concatena CSRT (Key) + Chave de Acesso
                # Nota: Algumas documentações dizem CSRT + Chave, outras Chave + CSRT.
                # A NT 2018.005 diz: "concatenação do CSRT com a Chave de Acesso da N-Fe" -> CSRT + Chave
                # Onde "CSRT" aqui se refere ao código alfanumérico (Key) de 16 a 36 caracteres.
                data = resp_dto.csrt_key + chave_acesso
                hash_bytes = hashlib.sha1(data.encode('utf-8')).digest()
                resp_dto.hash_csrt = base64.b64encode(hash_bytes).decode('utf-8')
                print(f"DEBUG: HashCSRT calculado: {resp_dto.hash_csrt} (Key={resp_dto.csrt_key}, Chave={chave_acesso})")
            else:
                print(f"DEBUG: Não foi possível calcular HashCSRT. ID da NFe inválido ou não encontrado: {nfe_id}")

        # Cria o grupo infRespTec
        resp = sub(inf_nfe, "infRespTec")
        sub(resp, "CNPJ", resp_dto.cnpj)
        sub(resp, "xContato", resp_dto.contato)
        sub(resp, "email", resp_dto.email)
        sub(resp, "fone", resp_dto.fone)
        
        if resp_dto.id_csrt:
            sub(resp, "idCSRT", resp_dto.id_csrt)
        if resp_dto.hash_csrt:
            sub(resp, "hashCSRT", resp_dto.hash_csrt)
