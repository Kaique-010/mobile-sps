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

    def _normalizar_xml_assinado(self, xml_assinado):
        if xml_assinado is None:
            return xml_assinado

        root = None
        if isinstance(xml_assinado, etree._Element):
            root = xml_assinado
        else:
            if isinstance(xml_assinado, (bytes, bytearray)):
                xml_assinado = xml_assinado.decode("utf-8", errors="ignore")

            if isinstance(xml_assinado, str):
                s = xml_assinado.strip()
                if not s:
                    return xml_assinado
                try:
                    root = etree.fromstring(s.encode("utf-8"))
                except Exception:
                    return xml_assinado
            else:
                return xml_assinado

        ns_nfe = "http://www.portalfiscal.inf.br/nfe"
        ns_ds = "http://www.w3.org/2000/09/xmldsig#"

        def qn(ns, tag):
            return f"{{{ns}}}{tag}"

        if root.tag in ("infNFe", qn(ns_nfe, "infNFe")):
            nfe_root = etree.Element(qn(ns_nfe, "NFe"))
            nfe_root.append(root)
            return nfe_root

        if root.tag not in ("NFe", qn(ns_nfe, "NFe")):
            return root

        inf_nodes = []
        for child in list(root):
            if child.tag in ("infNFe", qn(ns_nfe, "infNFe")):
                inf_nodes.append(child)

        if len(inf_nodes) <= 1:
            return root

        ref_uri = None
        ref = root.find(f".//{qn(ns_ds, 'Reference')}")
        if ref is not None:
            ref_uri = ref.get("URI") or None
        ref_id = (ref_uri or "").lstrip("#") or None

        inf_correto = None
        if ref_id:
            for node in inf_nodes:
                if node.get("Id") == ref_id:
                    inf_correto = node
                    break

        if inf_correto is None:
            for node in inf_nodes:
                if node.get("Id"):
                    inf_correto = node
                    break
        if inf_correto is None:
            inf_correto = inf_nodes[0]

        for node in inf_nodes:
            if node is not inf_correto and node.getparent() is root:
                root.remove(node)

        if inf_correto.getparent() is not root:
            try:
                inf_correto.getparent().remove(inf_correto)
            except Exception:
                pass
            root.insert(0, inf_correto)
        else:
            if list(root)[0] is not inf_correto:
                root.remove(inf_correto)
                root.insert(0, inf_correto)

        return root

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
        xml_assinado = self._normalizar_xml_assinado(xml_assinado)

        if hasattr(nota_fiscal, '_nfce_csc'):
            cfg = nota_fiscal._nfce_csc or {}
            try:
                self._injetar_qrcode_nfce(
                    xml_assinado,
                    id_token=str(cfg.get('id_token') or '').strip(),
                    csc=str(cfg.get('csc') or '').strip(),
                    uf=str(cfg.get('uf') or self.uf or '').strip(),
                    tp_amb=str(cfg.get('ambiente') or ('2' if self.homologacao else '1')).strip(),
                )
            except Exception as e:
                print(f"DEBUG: Falha ao injetar QRCode NFC-e: {e}")

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
            resposta = envio[1]

            if resposta and hasattr(resposta, 'text'):
                print("\n\n" + "="*50)
                print(f"=== SEFAZ ADAPTER RESPONSE (DEBUG TERMINAL) ===")
                print(f"STATUS HTTP: {getattr(resposta, 'status_code', 'N/A')}")
                print(f"CONTENT:\n{resposta.text}")
                print("="*50 + "\n\n")

            if resposta and hasattr(resposta, 'content'):
                try:
                    from lxml import etree
                    root = etree.fromstring(resposta.content)
                    ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}

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

                            ch_nfe_elem = inf_prot.find('.//ns:chNFe', namespaces=ns)
                            if ch_nfe_elem is not None:
                                chave = ch_nfe_elem.text

                    if status is None:
                        c_stat_elem = root.find('.//ns:cStat', namespaces=ns)
                        if c_stat_elem is not None:
                            status = int(c_stat_elem.text)

                        x_motivo_elem = root.find('.//ns:xMotivo', namespaces=ns)
                        if x_motivo_elem is not None:
                            motivo = x_motivo_elem.text

                except Exception as e_parse:
                    motivo = f"Erro ao parsear XML SEFAZ: {str(e_parse)}"

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
            modelo_envio = 'nfe'
            if len(chave) == 44:
                mod = chave[20:22]
                if mod == '65':
                    modelo_envio = 'nfce'

            print(f"\n=== CONSULTANDO CHAVE: {chave} (Modelo: {modelo_envio}) ===")
            resposta = self.comunicacao.consulta_nota(modelo=modelo_envio, chave=chave)

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

        tp_evento = '110111'
        n_seq_evento = 1

        evento = Evento(
            uf=self.uf,
            cnpj=cnpj,
            chave=chave,
            data_emissao=datetime.now(),
            tp_evento=tp_evento,
            n_seq_evento=n_seq_evento,
            descricao='Cancelamento',
            protocolo=str(protocolo),
            justificativa=justificativa,
            versao="1.00"
        )

        try:
            serializador = SerializacaoXML(_fonte_dados, homologacao=self.homologacao)
            xml_evento = serializador.serializar_evento(evento)
        except Exception as e_ser:
            import traceback
            traceback.print_exc()
            raise Exception(f"Erro na serialização do evento: {str(e_ser)} (Verifique logs para traceback)")

        if xml_evento is None:
            raise Exception(f"Falha na serialização do evento de cancelamento (xml_evento is None).")

        xml_assinado = self.assinador.assinar(xml_evento)

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
            if hasattr(resposta, 'content'):
                xml_retorno = resposta.content
            elif hasattr(resposta, 'text'):
                xml_retorno = resposta.text.encode('utf-8')
            else:
                xml_retorno = str(resposta).encode('utf-8')

            root = etree.fromstring(xml_retorno)
            ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}

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
        ns_uri = 'http://www.portalfiscal.inf.br/nfe'
        ns = {'ns': ns_uri}

        dh_emi = nfe_elem.findtext('.//ns:ide/ns:dhEmi', namespaces=ns) or nfe_elem.findtext('.//ide/dhEmi') or ""
        ano_emi = None
        if dh_emi and len(dh_emi) >= 4 and dh_emi[:4].isdigit():
            ano_emi = int(dh_emi[:4])

        dets = nfe_elem.findall('.//ns:det', namespaces=ns)

        if not dets:
            dets = nfe_elem.findall('.//det')

        print(f"DEBUG: _injetar_ibs_cbs: Encontrados {len(dets)} dets e {len(itens_extra)} itens_extra")

        if len(dets) != len(itens_extra):
            print("DEBUG: _injetar_ibs_cbs: Contagem incompatível. Abortando injeção.")
            return
        
        total_vbc = 0.0
        total_vcbs = 0.0
        total_vibs_uf = 0.0
        total_vibs_mun = 0.0

        for i, det in enumerate(dets):
            dados = itens_extra[i]

            imposto = det.find('.//ns:imposto', namespaces=ns)
            if imposto is None:
                imposto = det.find('.//imposto')

            if imposto is None:
                print(f"DEBUG: Item {i} sem tag imposto.")
                continue

            def fmt(v): return "{:.2f}".format(float(v or 0))

            def sub(parent, tag, text=None):
                if parent.tag.startswith('{'):
                    ns_prefix = parent.tag.split('}')[0] + '}'
                    elem = etree.SubElement(parent, f"{ns_prefix}{tag}")
                else:
                    elem = etree.SubElement(parent, tag)
                if text: elem.text = text
                return elem

            ibs_data = dados.get('ibs')
            cbs_data = dados.get('cbs')
            
            valor_ibs = float((ibs_data or {}).get('valor') or 0)
            valor_cbs = float((cbs_data or {}).get('valor') or 0)
            base_ibs = float((ibs_data or {}).get('base') or 0)
            base_cbs = float((cbs_data or {}).get('base') or 0)
            aliq_ibs = float((ibs_data or {}).get('aliq') or 0)
            aliq_cbs = float((cbs_data or {}).get('aliq') or 0)

            if valor_ibs <= 0 and valor_cbs <= 0:
                if ibs_data:
                    print(f"DEBUG: IBS zerado ({valor_ibs}), ignorando injeção para evitar erro 225.")
                if cbs_data:
                    print(f"DEBUG: CBS zerado ({valor_cbs}), ignorando injeção para evitar erro 225.")
                continue
            
            for node in list(imposto):
                if node.tag in ("IBS", "CBS", "IBSCBS", f"{{{ns_uri}}}IBS", f"{{{ns_uri}}}CBS", f"{{{ns_uri}}}IBSCBS"):
                    imposto.remove(node)
            
            vbc = base_cbs or base_ibs
            if not vbc:
                vprod = det.findtext('.//ns:prod/ns:vProd', namespaces=ns) or det.findtext('.//prod/vProd') or "0"
                vbc = float(vprod or 0)
            
            valor_ibs_mun = 0.0
            aliq_ibs_mun = 0.0
            aliq_ibs_uf = float(aliq_ibs or 0)
            if ano_emi in (2025, 2026):
                if aliq_ibs_uf > 0:
                    aliq_ibs_uf = 0.10
            elif ano_emi in (2027, 2028):
                if aliq_ibs_uf > 0:
                    aliq_ibs_uf = 0.05

            valor_ibs_uf = float(valor_ibs or 0)
            if aliq_ibs_uf != float(aliq_ibs or 0):
                valor_ibs_uf = round(float(vbc or 0) * (aliq_ibs_uf / 100.0), 2)

            vibs = float(valor_ibs or 0) + float(valor_ibs_mun or 0)

            ibscbs = sub(imposto, "IBSCBS")
            sub(ibscbs, "CST", "000")
            sub(ibscbs, "cClassTrib", "000001")
            gibscbs = sub(ibscbs, "gIBSCBS")
            sub(gibscbs, "vBC", fmt(vbc))
            gibuf = sub(gibscbs, "gIBSUF")
            sub(gibuf, "pIBSUF", fmt(aliq_ibs_uf))
            sub(gibuf, "vIBSUF", fmt(valor_ibs_uf))
            gibmun = sub(gibscbs, "gIBSMun")
            sub(gibmun, "pIBSMun", fmt(aliq_ibs_mun))
            sub(gibmun, "vIBSMun", fmt(valor_ibs_mun))
            sub(gibscbs, "vIBS", fmt(float(valor_ibs_uf or 0) + float(valor_ibs_mun or 0)))
            gcbs = sub(gibscbs, "gCBS")
            sub(gcbs, "pCBS", fmt(aliq_cbs))
            sub(gcbs, "vCBS", fmt(valor_cbs))
            
            total_vbc += float(vbc or 0)
            total_vcbs += float(valor_cbs or 0)
            total_vibs_uf += float(valor_ibs_uf or 0)
            total_vibs_mun += float(valor_ibs_mun or 0)

            print(f"DEBUG: Injetado IBS/CBS no item {i}")
        
        total = nfe_elem.find('.//ns:total', namespaces=ns) or nfe_elem.find('.//total')
        if total is None:
            return
        
        for node in list(total):
            if node.tag in ("IBSCBSTot", f"{{{ns_uri}}}IBSCBSTot"):
                total.remove(node)
        
        if total_vbc > 0 or total_vcbs > 0 or total_vibs_uf > 0 or total_vibs_mun > 0:
            tot = sub(total, "IBSCBSTot")
            sub(tot, "vBCIBSCBS", fmt(total_vbc))
            gibs = sub(tot, "gIBS")
            gibsuf = sub(gibs, "gIBSUF")
            sub(gibsuf, "vDif", fmt(0))
            sub(gibsuf, "vDevTrib", fmt(0))
            sub(gibsuf, "vIBSUF", fmt(total_vibs_uf))
            gibsmun = sub(gibs, "gIBSMun")
            sub(gibsmun, "vDif", fmt(0))
            sub(gibsmun, "vDevTrib", fmt(0))
            sub(gibsmun, "vIBSMun", fmt(total_vibs_mun))
            sub(gibs, "vIBS", fmt(total_vibs_uf + total_vibs_mun))
            sub(gibs, "vCredPres", fmt(0))
            sub(gibs, "vCredPresCondSus", fmt(0))

            gcbs = sub(tot, "gCBS")
            sub(gcbs, "vDif", fmt(0))
            sub(gcbs, "vDevTrib", fmt(0))
            sub(gcbs, "vCBS", fmt(total_vcbs))
            sub(gcbs, "vCredPres", fmt(0))
            sub(gcbs, "vCredPresCondSus", fmt(0))

    def _injetar_responsavel_tecnico(self, nfe_elem, resp_dto):
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

        inf_nfe = nfe_elem.find('.//ns:infNFe', namespaces=ns)
        if inf_nfe is None:
            inf_nfe = nfe_elem.find('.//infNFe')

        if inf_nfe is None:
            print("DEBUG: _injetar_responsavel_tecnico: infNFe não encontrado.")
            return

        print(f"DEBUG: Injetando infRespTec para CNPJ {resp_dto.cnpj}")

        if resp_dto.csrt_key and not resp_dto.hash_csrt:
            nfe_id = inf_nfe.get("Id")
            if nfe_id and nfe_id.startswith("NFe"):
                chave_acesso = nfe_id[3:]
                data = resp_dto.csrt_key + chave_acesso
                hash_bytes = hashlib.sha1(data.encode('utf-8')).digest()
                resp_dto.hash_csrt = base64.b64encode(hash_bytes).decode('utf-8')
                print(f"DEBUG: HashCSRT calculado: {resp_dto.hash_csrt} (Key={resp_dto.csrt_key}, Chave={chave_acesso})")
            else:
                print(f"DEBUG: Não foi possível calcular HashCSRT. ID da NFe inválido ou não encontrado: {nfe_id}")

        resp = sub(inf_nfe, "infRespTec")
        sub(resp, "CNPJ", resp_dto.cnpj)
        sub(resp, "xContato", resp_dto.contato)
        sub(resp, "email", resp_dto.email)
        sub(resp, "fone", resp_dto.fone)

        if resp_dto.id_csrt:
            sub(resp, "idCSRT", resp_dto.id_csrt)
        if resp_dto.hash_csrt:
            sub(resp, "hashCSRT", resp_dto.hash_csrt)

    def _injetar_qrcode_nfce(self, nfe_elem, id_token, csc, uf, tp_amb):
        if not id_token or not csc:
            return

        id_token = str(id_token).strip()
        csc = str(csc).strip()
        if id_token.isdigit():
            id_token = str(int(id_token))

        uf = (uf or "").strip().upper()
        if uf == "PR":
            base_qr = "http://www.fazenda.pr.gov.br/nfce/qrcode?"
            url_chave = "http://www.fazenda.pr.gov.br/nfce/consulta"
        else:
            raise Exception(f"UF sem URL de QRCode configurada: {uf}")

        ns_uri = "http://www.portalfiscal.inf.br/nfe"
        ns_ds  = "http://www.w3.org/2000/09/xmldsig#"
        ns     = {"ns": ns_uri, "ds": ns_ds}

        inf_nfe = nfe_elem.find(".//ns:infNFe", namespaces=ns) or nfe_elem.find(".//infNFe")
        if inf_nfe is None:
            raise Exception("infNFe não encontrado")

        nfe_id = inf_nfe.get("Id") or ""
        chave  = nfe_id[3:] if nfe_id.startswith("NFe") else nfe_id
        if not chave or len(chave) != 44:
            raise Exception("Chave de acesso inválida para QRCode")

        ide = inf_nfe.find(".//ns:ide", namespaces=ns) or inf_nfe.find(".//ide")
        if ide is None:
            raise Exception("ide não encontrado")

        tp_amb_xml = ide.findtext(".//ns:tpAmb", namespaces=ns) or ide.findtext(".//tpAmb") or ""
        if tp_amb_xml.strip():
            tp_amb = tp_amb_xml.strip()

        dest   = inf_nfe.find(".//ns:dest", namespaces=ns) or inf_nfe.find(".//dest")
        c_dest = ""
        if dest is not None:
            c_dest = (
                dest.findtext(".//ns:CNPJ", namespaces=ns) or dest.findtext(".//CNPJ") or
                dest.findtext(".//ns:CPF",  namespaces=ns) or dest.findtext(".//CPF")  or ""
            )
        c_dest = "".join(ch for ch in str(c_dest) if ch.isdigit())

        v_nf = (
            inf_nfe.findtext(".//ns:total/ns:ICMSTot/ns:vNF", namespaces=ns)
            or inf_nfe.findtext(".//total/ICMSTot/vNF") or ""
        ).strip()
        if not v_nf:
            raise Exception("vNF não encontrado")

        dig_val = (
            nfe_elem.findtext(".//ds:Reference/ds:DigestValue", namespaces=ns)
            or nfe_elem.findtext(".//DigestValue") or ""
        ).strip()
        if not dig_val:
            raise Exception("DigestValue não encontrado")

        n_versao = "2"
        # cDest para NFC-e: "1" se destinatário identificado, "0" se anônimo
        # Baseado em exemplos reais do PR: o campo é apenas 1 dígito
        c_dest_qr = "1" if c_dest else "0"

        url_core = f"{chave}|{n_versao}|{tp_amb}|{id_token}"
        hash_bytes = hashlib.sha1((url_core + csc).encode("utf-8")).digest()
        hash_hex = base64.b16encode(hash_bytes).decode("utf-8")

        qr_url = f"{base_qr}p={url_core}|{hash_hex}"
        print(f"DEBUG: QRCode URL COMPLETA: {qr_url}")

        # Helper local com nome único para evitar conflito com funções 'sub' de outros métodos
        def _sub_qr(parent, tag, text=None):
            ns_prefix = ""
            if parent.tag.startswith("{"):
                ns_prefix = parent.tag.split("}")[0] + "}"
            elem = etree.SubElement(parent, f"{ns_prefix}{tag}")
            if text is not None:
                elem.text = str(text)
            return elem

        # Localiza ou cria infNFeSupl
        inf_supl = None
        for child in list(nfe_elem):
            if child.tag in ("infNFeSupl", f"{{{ns_uri}}}infNFeSupl"):
                inf_supl = child
                break

        if inf_supl is None:
            inf_supl = etree.Element(
                f"{{{ns_uri}}}infNFeSupl" if nfe_elem.tag.startswith("{") else "infNFeSupl"
            )
            children = list(nfe_elem)
            idx_inf = next((i for i, c in enumerate(children) if c.tag in ("infNFe", f"{{{ns_uri}}}infNFe")), None)
            idx_sig = next((i for i, c in enumerate(children) if c.tag in ("Signature", f"{{{ns_ds}}}Signature")), None)
            insert_at = idx_sig if idx_sig is not None else len(children)
            if idx_inf is not None and insert_at <= idx_inf:
                insert_at = idx_inf + 1
            nfe_elem.insert(insert_at, inf_supl)

        # Limpa nós antigos de qrCode/urlChave
        for node in list(inf_supl):
            if node.tag in ("qrCode", f"{{{ns_uri}}}qrCode", "urlChave", f"{{{ns_uri}}}urlChave"):
                inf_supl.remove(node)

        _sub_qr(inf_supl, "qrCode", qr_url)
        _sub_qr(inf_supl, "urlChave", url_chave)

        print(f"DEBUG: infNFeSupl XML: {etree.tostring(inf_supl, encoding='unicode')}")
