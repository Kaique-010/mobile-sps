# -*- coding: utf-8 -*-
from lxml import etree
from datetime import datetime

NFE_NS = "http://www.portalfiscal.inf.br/nfe"
NSMAP = {None: NFE_NS}


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

    # ----------------------------------------------------------------------
    # itens
    # ----------------------------------------------------------------------
    def _det(self, root, itens):
        for i, item in enumerate(itens, start=1):
            det = etree.SubElement(root, "det", nItem=str(i))
            prod = etree.SubElement(det, "prod")

            quantidade = float(item["quantidade"])
            unit = float(item["valor_unit"])
            desconto = float(item.get("desconto", 0))
            vprod = quantidade * unit

            etree.SubElement(prod, "cProd").text = item["codigo"]
            etree.SubElement(prod, "xProd").text = item["descricao"]
            etree.SubElement(prod, "NCM").text = item["ncm"]
            etree.SubElement(prod, "CFOP").text = item["cfop"]
            etree.SubElement(prod, "uCom").text = item["unidade"]
            etree.SubElement(prod, "qCom").text = f"{quantidade:.4f}"
            etree.SubElement(prod, "vUnCom").text = f"{unit:.10f}"
            etree.SubElement(prod, "vProd").text = f"{vprod:.2f}"

            if desconto > 0:
                etree.SubElement(prod, "vDesc").text = f"{desconto:.2f}"

            # imposto mínimo (ICMS CST padrão)
            imposto = etree.SubElement(det, "imposto")
            icms_group = etree.SubElement(imposto, "ICMS")

            cst = item["cst_icms"]
            icms_tag = f"ICMS{cst}"

            ic = etree.SubElement(icms_group, icms_tag)
            etree.SubElement(ic, "orig").text = "0"
            etree.SubElement(ic, "CST").text = cst

    # ----------------------------------------------------------------------
    # total
    # ----------------------------------------------------------------------
    def _total(self, root, dto):
        total = etree.SubElement(root, "total")
        icms = etree.SubElement(total, "ICMSTot")

        vprod = sum(float(i["quantidade"]) * float(i["valor_unit"]) for i in dto["itens"])
        vdesc = sum(float(i.get("desconto", 0)) for i in dto["itens"])
        vnf = vprod - vdesc

        def zero(): return "0.00"

        etree.SubElement(icms, "vBC").text = zero()
        etree.SubElement(icms, "vICMS").text = zero()
        etree.SubElement(icms, "vICMSDeson").text = zero()
        etree.SubElement(icms, "vFCPUFDest").text = zero()
        etree.SubElement(icms, "vICMSUFDest").text = zero()
        etree.SubElement(icms, "vICMSUFRemet").text = zero()
        etree.SubElement(icms, "vFCP").text = zero()
        etree.SubElement(icms, "vBCST").text = zero()
        etree.SubElement(icms, "vST").text = zero()
        etree.SubElement(icms, "vFCPST").text = zero()
        etree.SubElement(icms, "vFCPSTRet").text = zero()
        etree.SubElement(icms, "vProd").text = f"{vprod:.2f}"
        etree.SubElement(icms, "vFrete").text = zero()
        etree.SubElement(icms, "vSeg").text = zero()
        etree.SubElement(icms, "vDesc").text = f"{vdesc:.2f}"
        etree.SubElement(icms, "vII").text = zero()
        etree.SubElement(icms, "vIPI").text = zero()
        etree.SubElement(icms, "vIPIDevol").text = zero()
        etree.SubElement(icms, "vPIS").text = zero()
        etree.SubElement(icms, "vCOFINS").text = zero()
        etree.SubElement(icms, "vOutro").text = zero()
        etree.SubElement(icms, "vNF").text = f"{vnf:.2f}"
        etree.SubElement(icms, "vTotTrib").text = zero()

    # ----------------------------------------------------------------------
    # pagamentos
    # ----------------------------------------------------------------------
    def _pag(self, root, dto):
        pag = etree.SubElement(root, "pag")
        det = etree.SubElement(pag, "detPag")

        tpag = dto.get("tpag") or "01"
        etree.SubElement(det, "tPag").text = tpag

        vprod = sum(float(i["quantidade"]) * float(i["valor_unit"]) for i in dto["itens"])
        vdesc = sum(float(i.get("desconto", 0)) for i in dto["itens"])
        etree.SubElement(det, "vPag").text = f"{(vprod - vdesc):.2f}"

    # ----------------------------------------------------------------------
    # responsável técnico
    # ----------------------------------------------------------------------
    def _resp_tecnico(self, root):
        r = etree.SubElement(root, "infRespTec")
        etree.SubElement(r, "CNPJ").text = "20702018000142"
        etree.SubElement(r, "xContato").text = "SPS Web"
        etree.SubElement(r, "email").text = "suporte@spartacus.com.br"
