# -*- coding: utf-8 -*-
from lxml import etree
from datetime import datetime
import logging

NFE_NS = "http://www.portalfiscal.inf.br/nfe"
NSMAP = {None: NFE_NS}
logger = logging.getLogger(__name__)


class GeradorXML:
    """
    Gerador de XML NF-e 4.00.
    - NÃO adiciona campos proibidos (tpAmb dentro do infNFe)
    - NÃO adiciona namespaces duplicados
    - XML limpo e aceito por todos os estados
    """

    def gerar(self, dto: dict) -> str:
        chave = dto.get("chave")
        if not chave:
            raise ValueError("DTO sem chave (campo 'chave').")

        nfe_id = f"NFe{chave}"

        logger.debug("GeradorXML.gerar: DTO recebido para chave %s: %s", chave, dto)

        root = etree.Element("NFe", nsmap=NSMAP)
        inf = etree.SubElement(root, "infNFe", Id=nfe_id, versao="4.00")

        self._ide(inf, dto)
        self._emit(inf, dto["emitente"])
        self._dest(inf, dto["destinatario"])
        self._det(inf, dto["itens"])
        self._total(inf, dto)
        self._pag(inf, dto)
        self._resp_tecnico(root)

        xml = etree.tostring(
            root,
            encoding="utf-8",
            pretty_print=False,
            xml_declaration=False,
        ).decode("utf-8")

        logger.debug("GeradorXML.gerar: XML gerado para chave %s: %s", chave, xml)

        return xml

    # ----------------------------------------------------------------------
    # ide
    # ----------------------------------------------------------------------
    def _ide(self, root, dto):
        ide = etree.SubElement(root, "ide")

        emit_uf = dto["emitente"]["uf"]
        dest_uf = dto["destinatario"]["uf"]
        id_dest = "2" if emit_uf != dest_uf else "1"

        cuf = dto["emitente"]["cUF"]

        etree.SubElement(ide, "cUF").text = cuf
        etree.SubElement(ide, "cNF").text = dto["cNF"]                # obrigatório
        etree.SubElement(ide, "natOp").text = dto.get("natOp", "VENDA")

        etree.SubElement(ide, "mod").text = str(dto.get("modelo", "55"))
        etree.SubElement(ide, "serie").text = str(dto.get("serie", "1"))
        etree.SubElement(ide, "nNF").text = str(dto["numero"])

        dh_emi = dto.get("data_emissao") or datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
        etree.SubElement(ide, "dhEmi").text = dh_emi

        etree.SubElement(ide, "tpNF").text = str(dto.get("tipo_operacao", 1))
        etree.SubElement(ide, "idDest").text = id_dest

        # NÃO colocar tpAmb aqui (PROÍBIDO no schema)
        # Ambiente é no enviNFe, não na tag ide.

        etree.SubElement(ide, "tpImp").text = "1"
        etree.SubElement(ide, "tpEmis").text = "1"

        etree.SubElement(ide, "finNFe").text = str(dto.get("finalidade", 1))
        etree.SubElement(ide, "indFinal").text = "1"
        etree.SubElement(ide, "indPres").text = "1"

        etree.SubElement(ide, "procEmi").text = "0"
        etree.SubElement(ide, "verProc").text = "SPS-ERP-1.0"

    # ----------------------------------------------------------------------
    # emitente
    # ----------------------------------------------------------------------
    def _emit(self, root, emit):
        e = etree.SubElement(root, "emit")

        etree.SubElement(e, "CNPJ").text = emit["cnpj"].zfill(14)
        etree.SubElement(e, "xNome").text = emit["razao"]
        etree.SubElement(e, "IE").text = emit["ie"]

        end = etree.SubElement(e, "enderEmit")
        etree.SubElement(end, "xLgr").text = emit["logradouro"]
        etree.SubElement(end, "nro").text = emit["numero"]
        etree.SubElement(end, "xBairro").text = emit.get("bairro", "CENTRO")
        etree.SubElement(end, "cMun").text = emit["cod_municipio"]
        etree.SubElement(end, "xMun").text = emit["municipio"]
        etree.SubElement(end, "UF").text = emit["uf"]
        etree.SubElement(end, "CEP").text = emit["cep"]

    # ----------------------------------------------------------------------
    # destinatário
    # ----------------------------------------------------------------------
    def _dest(self, root, dest):
        d = etree.SubElement(root, "dest")

        doc = dest["documento"]
        if len(doc) == 11:
            etree.SubElement(d, "CPF").text = doc
        else:
            etree.SubElement(d, "CNPJ").text = doc

        etree.SubElement(d, "xNome").text = dest["nome"]

        end = etree.SubElement(d, "enderDest")
        etree.SubElement(end, "xLgr").text = dest["logradouro"]
        etree.SubElement(end, "nro").text = dest["numero"]
        etree.SubElement(end, "xBairro").text = dest["bairro"]
        etree.SubElement(end, "cMun").text = dest["cod_municipio"]
        etree.SubElement(end, "xMun").text = dest["municipio"]
        etree.SubElement(end, "UF").text = dest["uf"]
        etree.SubElement(end, "CEP").text = dest["cep"]

    def _f(self, val):
        if val is None:
            return 0.0
        return float(val)

    # ----------------------------------------------------------------------
    # itens
    # ----------------------------------------------------------------------
    def _det(self, root, itens):
        for i, item in enumerate(itens, start=1):
            det = etree.SubElement(root, "det", nItem=str(i))
            prod = etree.SubElement(det, "prod")

            quantidade = self._f(item["quantidade"])
            unit = self._f(item["valor_unit"])
            desconto = self._f(item.get("desconto", 0))
            vprod = quantidade * unit

            etree.SubElement(prod, "cProd").text = item["codigo"]
            etree.SubElement(prod, "xProd").text = item["descricao"]
            etree.SubElement(prod, "NCM").text = item["ncm"]
            
            if item.get("cest"):
                etree.SubElement(prod, "CEST").text = item["cest"]

            etree.SubElement(prod, "CFOP").text = item["cfop"]
            etree.SubElement(prod, "uCom").text = item["unidade"]
            etree.SubElement(prod, "qCom").text = f"{quantidade:.4f}"
            etree.SubElement(prod, "vUnCom").text = f"{unit:.10f}"
            etree.SubElement(prod, "vProd").text = f"{vprod:.2f}"
            
            # Frete, Seguro e Outras Despesas no Item
            vfrete = self._f(item.get("valor_frete"))
            if vfrete > 0:
                etree.SubElement(prod, "vFrete").text = f"{vfrete:.2f}"
                
            vseg = self._f(item.get("valor_seguro"))
            if vseg > 0:
                etree.SubElement(prod, "vSeg").text = f"{vseg:.2f}"
                
            voutro = self._f(item.get("valor_outras_despesas"))
            if voutro > 0:
                etree.SubElement(prod, "vOutro").text = f"{voutro:.2f}"

            if desconto > 0:
                etree.SubElement(prod, "vDesc").text = f"{desconto:.2f}"

            imposto = etree.SubElement(det, "imposto")
            
            # Chama os geradores de cada imposto
            self._icms(imposto, item)
            self._ipi(imposto, item)
            self._pis(imposto, item)
            self._cofins(imposto, item)
            self._ibs(imposto, item)
            self._cbs(imposto, item)

    def _icms(self, parent, item):
        icms = etree.SubElement(parent, "ICMS")
        cst = item["cst_icms"]
        orig = "0"  # Idealmente viria do item/produto

        def f2(v): return f"{self._f(v):.2f}"

        if len(cst) == 3:  # Simples Nacional (CSOSN)
            tag = f"ICMSSN{cst}"
            group = etree.SubElement(icms, tag)
            etree.SubElement(group, "orig").text = orig
            etree.SubElement(group, "CSOSN").text = cst
            
            if cst == "101":
                # pCredSN e vCredICMSSN
                pass # Implementar se tiver dados
            elif cst in ("201", "202", "203", "900"):
                if cst == "201":
                   # 201 também tem crédito
                   pass 
                
                # Campos ST para SN
                etree.SubElement(group, "modBCST").text = "4" # Margem Valor Agregado
                
                vbc_st = self._f(item.get("base_icms_st"))
                if vbc_st > 0:
                    etree.SubElement(group, "pMVAST").text = f2(item.get("mva_st"))
                    etree.SubElement(group, "vBCST").text = f2(vbc_st)
                    etree.SubElement(group, "pICMSST").text = f2(item.get("aliq_icms_st"))
                    etree.SubElement(group, "vICMSST").text = f2(item.get("valor_icms_st"))

                if cst == "900":
                    # 900 tem campos de ICMS próprio também
                    etree.SubElement(group, "modBC").text = "3"
                    etree.SubElement(group, "vBC").text = f2(item.get("base_icms"))
                    etree.SubElement(group, "pICMS").text = f2(item.get("aliq_icms"))
                    etree.SubElement(group, "vICMS").text = f2(item.get("valor_icms"))

        else:
            tag = f"ICMS{cst}"
            if cst == "41" or cst == "50": # Repasse, Não Tributado
                 tag = "ICMS40"
            
            group = etree.SubElement(icms, tag)
            etree.SubElement(group, "orig").text = orig
            etree.SubElement(group, "CST").text = cst

            if cst in ("00", "10", "20", "51", "70", "90"):
                etree.SubElement(group, "modBC").text = "3" # Valor Operação
                etree.SubElement(group, "vBC").text = f2(item.get("base_icms"))
                etree.SubElement(group, "pICMS").text = f2(item.get("aliq_icms"))
                etree.SubElement(group, "vICMS").text = f2(item.get("valor_icms"))

            if cst in ("10", "30", "70", "90"):
                 etree.SubElement(group, "modBCST").text = "4"
                 vbc_st = self._f(item.get("base_icms_st"))
                 if vbc_st > 0 or cst in ("10", "70"): # 10 e 70 exigem ST, 30 e 90 podem ser isentos
                    etree.SubElement(group, "pMVAST").text = f2(item.get("mva_st"))
                    etree.SubElement(group, "vBCST").text = f2(vbc_st)
                    etree.SubElement(group, "pICMSST").text = f2(item.get("aliq_icms_st"))
                    etree.SubElement(group, "vICMSST").text = f2(item.get("valor_icms_st"))

    def _ipi(self, parent, item):
        cst = item.get("cst_ipi")
        if not cst: return

        ipi = etree.SubElement(parent, "IPI")
        etree.SubElement(ipi, "cEnq").text = "999" # Genérico

        if cst in ("00", "49", "50", "99"):
            ipitrib = etree.SubElement(ipi, f"IPITrib")
            etree.SubElement(ipitrib, "CST").text = cst
            etree.SubElement(ipitrib, "vBC").text = f"{self._f(item.get('base_ipi')):.2f}"
            etree.SubElement(ipitrib, "pIPI").text = f"{self._f(item.get('aliq_ipi')):.2f}"
            etree.SubElement(ipitrib, "vIPI").text = f"{self._f(item.get('valor_ipi')):.2f}"
        else:
            ipint = etree.SubElement(ipi, "IPINT")
            etree.SubElement(ipint, "CST").text = cst

    def _pis(self, parent, item):
        cst = item["cst_pis"]
        pis = etree.SubElement(parent, "PIS")
        
        if cst in ("01", "02"):
            group = etree.SubElement(pis, "PISAliq")
            etree.SubElement(group, "CST").text = cst
            etree.SubElement(group, "vBC").text = f"{self._f(item.get('base_pis')):.2f}"
            etree.SubElement(group, "pPIS").text = f"{self._f(item.get('aliq_pis')):.2f}"
            etree.SubElement(group, "vPIS").text = f"{self._f(item.get('valor_pis')):.2f}"
        elif cst == "99":
            group = etree.SubElement(pis, "PISOutr")
            etree.SubElement(group, "CST").text = cst
            etree.SubElement(group, "vBC").text = f"{self._f(item.get('base_pis')):.2f}"
            etree.SubElement(group, "pPIS").text = f"{self._f(item.get('aliq_pis')):.2f}"
            etree.SubElement(group, "vPIS").text = f"{self._f(item.get('valor_pis')):.2f}"
        else:
            group = etree.SubElement(pis, "PISNT")
            etree.SubElement(group, "CST").text = cst

    def _cofins(self, parent, item):
        cst = item["cst_cofins"]
        cofins = etree.SubElement(parent, "COFINS")
        
        if cst in ("01", "02"):
            group = etree.SubElement(cofins, "COFINSAliq")
            etree.SubElement(group, "CST").text = cst
            etree.SubElement(group, "vBC").text = f"{self._f(item.get('base_cofins')):.2f}"
            etree.SubElement(group, "pCOFINS").text = f"{self._f(item.get('aliq_cofins')):.2f}"
            etree.SubElement(group, "vCOFINS").text = f"{self._f(item.get('valor_cofins')):.2f}"
        elif cst == "99":
            group = etree.SubElement(cofins, "COFINSOutr")
            etree.SubElement(group, "CST").text = cst
            etree.SubElement(group, "vBC").text = f"{self._f(item.get('base_cofins')):.2f}"
            etree.SubElement(group, "pCOFINS").text = f"{self._f(item.get('aliq_cofins')):.2f}"
            etree.SubElement(group, "vCOFINS").text = f"{self._f(item.get('valor_cofins')):.2f}"
        else:
            group = etree.SubElement(cofins, "COFINSNT")
            etree.SubElement(group, "CST").text = cst

    def _ibs(self, parent, item):
        # NT 2023.004
        val = self._f(item.get("valor_ibs"))
        if val <= 0: return

        ibs = etree.SubElement(parent, "IBS")
        # Por enquanto simplificado, pois o schema final pode variar
        # Usando tags genéricas baseadas na proposta
        etree.SubElement(ibs, "vBCIBS").text = f"{self._f(item.get('base_ibs')):.2f}"
        etree.SubElement(ibs, "pIBS").text = f"{self._f(item.get('aliq_ibs')):.2f}"
        etree.SubElement(ibs, "vIBS").text = f"{val:.2f}"

    def _cbs(self, parent, item):
        # NT 2023.004
        val = self._f(item.get("valor_cbs"))
        if val <= 0: return

        cbs = etree.SubElement(parent, "CBS")
        etree.SubElement(cbs, "vBCCBS").text = f"{self._f(item.get('base_cbs')):.2f}"
        etree.SubElement(cbs, "pCBS").text = f"{self._f(item.get('aliq_cbs')):.2f}"
        etree.SubElement(cbs, "vCBS").text = f"{val:.2f}"
    
    # ----------------------------------------------------------------------
    # total
    # ----------------------------------------------------------------------
    def _total(self, root, dto):
        total = etree.SubElement(root, "total")
        icms = etree.SubElement(total, "ICMSTot")

        vprod = sum(self._f(i["quantidade"]) * self._f(i["valor_unit"]) for i in dto["itens"])
        vdesc = sum(self._f(i.get("desconto", 0)) for i in dto["itens"])
        
        # Sumariza Impostos
        vbc_icms = sum(self._f(i.get("base_icms")) for i in dto["itens"])
        vicms = sum(self._f(i.get("valor_icms")) for i in dto["itens"])
        
        vbc_st = sum(self._f(i.get("base_icms_st")) for i in dto["itens"])
        vst = sum(self._f(i.get("valor_icms_st")) for i in dto["itens"])
        
        vipi = sum(self._f(i.get("valor_ipi")) for i in dto["itens"])
        vpis = sum(self._f(i.get("valor_pis")) for i in dto["itens"])
        vcofins = sum(self._f(i.get("valor_cofins")) for i in dto["itens"])
        vfcp = sum(self._f(i.get("valor_fcp")) for i in dto["itens"])
        
        vibs = sum(self._f(i.get("valor_ibs")) for i in dto["itens"])
        vcbs = sum(self._f(i.get("valor_cbs")) for i in dto["itens"])

        vfrete = sum(self._f(i.get("valor_frete")) for i in dto["itens"])
        vseg = sum(self._f(i.get("valor_seguro")) for i in dto["itens"])
        voutro = sum(self._f(i.get("valor_outras_despesas")) for i in dto["itens"])

        # Total da Nota = Prod - Desc + IPI + ST + Frete + Seg + Outro + II - ICMSDeson
        # vNF = vProd - vDesc - vICMSDeson + vST + vFrete + vSeg + vOutro + vII + vIPI + vIPIDevol + vFCPST
        # + IBS + CBS (Reforma Tributária - assumindo taxa por fora)
        
        vnf = vprod - vdesc + vipi + vst + vfrete + vseg + voutro + vibs + vcbs

        def zero(): return "0.00"
        def f2(v): return f"{v:.2f}"

        etree.SubElement(icms, "vBC").text = f2(vbc_icms)
        etree.SubElement(icms, "vICMS").text = f2(vicms)
        etree.SubElement(icms, "vICMSDeson").text = zero()
        etree.SubElement(icms, "vFCPUFDest").text = zero()
        etree.SubElement(icms, "vICMSUFDest").text = zero()
        etree.SubElement(icms, "vICMSUFRemet").text = zero()
        etree.SubElement(icms, "vFCP").text = f2(vfcp)
        etree.SubElement(icms, "vBCST").text = f2(vbc_st)
        etree.SubElement(icms, "vST").text = f2(vst)
        etree.SubElement(icms, "vFCPST").text = zero()
        etree.SubElement(icms, "vFCPSTRet").text = zero()
        etree.SubElement(icms, "vProd").text = f2(vprod)
        etree.SubElement(icms, "vFrete").text = f2(vfrete)
        etree.SubElement(icms, "vSeg").text = f2(vseg)
        etree.SubElement(icms, "vDesc").text = f2(vdesc)
        etree.SubElement(icms, "vII").text = zero()
        etree.SubElement(icms, "vIPI").text = f2(vipi)
        etree.SubElement(icms, "vIPIDevol").text = zero()
        etree.SubElement(icms, "vPIS").text = f2(vpis)
        etree.SubElement(icms, "vCOFINS").text = f2(vcofins)
        etree.SubElement(icms, "vOutro").text = f2(voutro)
        etree.SubElement(icms, "vNF").text = f2(vnf)
        etree.SubElement(icms, "vTotTrib").text = zero()

    # ----------------------------------------------------------------------
    # pagamentos
    # ----------------------------------------------------------------------
    def _pag(self, root, dto):
        pag = etree.SubElement(root, "pag")
        det = etree.SubElement(pag, "detPag")

        tpag = dto.get("tpag") or "01"
        etree.SubElement(det, "tPag").text = tpag

        # Recalcula vNF para pagamento (mesma lógica do _total)
        vprod = sum(self._f(i["quantidade"]) * self._f(i["valor_unit"]) for i in dto["itens"])
        vdesc = sum(self._f(i.get("desconto", 0)) for i in dto["itens"])
        
        vst = sum(self._f(i.get("valor_icms_st")) for i in dto["itens"])
        vipi = sum(self._f(i.get("valor_ipi")) for i in dto["itens"])
        vfrete = sum(self._f(i.get("valor_frete")) for i in dto["itens"])
        vseg = sum(self._f(i.get("valor_seguro")) for i in dto["itens"])
        voutro = sum(self._f(i.get("valor_outras_despesas")) for i in dto["itens"])
        
        vibs = sum(self._f(i.get("valor_ibs")) for i in dto["itens"])
        vcbs = sum(self._f(i.get("valor_cbs")) for i in dto["itens"])
        
        # vNF = vProd - vDesc - vICMSDeson + vST + vFrete + vSeg + vOutro + vII + vIPI + vIPIDevol + vFCPST
        vnf = vprod - vdesc + vipi + vst + vfrete + vseg + voutro + vibs + vcbs
        
        etree.SubElement(det, "vPag").text = f"{vnf:.2f}"

    # ----------------------------------------------------------------------
    # responsável técnico
    # ----------------------------------------------------------------------
    def _resp_tecnico(self, root):
        r = etree.SubElement(root, "infRespTec")
        etree.SubElement(r, "CNPJ").text = "20702018000142"
        etree.SubElement(r, "xContato").text = "SPS Web"
        etree.SubElement(r, "email").text = "suporte@spartacus.com.br"
