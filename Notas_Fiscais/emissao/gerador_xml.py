from lxml import etree


class GeradorXML:

    NAMESPACE = {
        None: "http://www.portalfiscal.inf.br/nfe"
    }

    def gerar(self, dto):
        """
        Gera XML base NF-e 4.00 sem assinatura
        """
        NFe = etree.Element("NFe", nsmap=self.NAMESPACE)
        inf = etree.SubElement(NFe, "infNFe", Id="NFeTEMP", versao="4.00")

        self._ide(inf, dto)
        self._emit(inf, dto["emitente"])
        self._dest(inf, dto["destinatario"])
        self._det(inf, dto["itens"])
        self._total(inf, dto)
        self._pag(inf, dto)
        self._resp_tecnico(inf)

        return etree.tostring(
            NFe,
            encoding="utf-8",
            pretty_print=False,
            xml_declaration=False,
        ).decode()

    # --------------------------------------------------------------
    def _ide(self, root, dto):
        ide = etree.SubElement(root, "ide")
        emit_uf = dto["emitente"]["uf"]
        dest_uf = dto["destinatario"]["uf"]
        id_dest = "2" if emit_uf and dest_uf and emit_uf != dest_uf else "1"

        etree.SubElement(ide, "cUF").text = self._uf_to_cuf(emit_uf)
        etree.SubElement(ide, "natOp").text = "VENDA"
        etree.SubElement(ide, "mod").text = str(dto.get("modelo", "55"))
        etree.SubElement(ide, "serie").text = str(dto.get("serie", "1"))
        etree.SubElement(ide, "nNF").text = str(dto.get("numero", 0))
        etree.SubElement(ide, "tpNF").text = str(dto.get("tipo_operacao", 1))
        etree.SubElement(ide, "idDest").text = id_dest
        etree.SubElement(ide, "tpImp").text = "1"
        etree.SubElement(ide, "tpEmis").text = "1"
        etree.SubElement(ide, "tpAmb").text = str(dto.get("ambiente", 2))
        etree.SubElement(ide, "finNFe").text = str(dto.get("finalidade", 1))
        etree.SubElement(ide, "indFinal").text = "1"
        etree.SubElement(ide, "indPres").text = "1"
        etree.SubElement(ide, "procEmi").text = "0"
        etree.SubElement(ide, "verProc").text = "SPS-ERP-1.0"

    # --------------------------------------------------------------
    def _emit(self, root, emit):
        e = etree.SubElement(root, "emit")
        etree.SubElement(e, "CNPJ").text = emit.get("cnpj")
        etree.SubElement(e, "xNome").text = emit.get("razao")
        etree.SubElement(e, "IE").text = emit.get("ie")

        ender = etree.SubElement(e, "enderEmit")
        etree.SubElement(ender, "xLgr").text = emit.get("logradouro")
        etree.SubElement(ender, "nro").text = emit.get("numero")
        etree.SubElement(ender, "xBairro").text = emit.get("bairro")
        etree.SubElement(ender, "cMun").text = str(emit.get("cod_municipio") or "9999999")
        etree.SubElement(ender, "xMun").text = emit.get("municipio")
        etree.SubElement(ender, "UF").text = emit.get("uf")
        etree.SubElement(ender, "CEP").text = emit.get("cep")

    # --------------------------------------------------------------
    def _dest(self, root, dest):
        d = etree.SubElement(root, "dest")

        doc = dest.get("documento") or ""
        if len(doc) == 11:
            etree.SubElement(d, "CPF").text = doc
        else:
            etree.SubElement(d, "CNPJ").text = doc

        etree.SubElement(d, "xNome").text = dest.get("nome")

        ender = etree.SubElement(d, "enderDest")
        etree.SubElement(ender, "xLgr").text = dest.get("logradouro")
        etree.SubElement(ender, "nro").text = dest.get("numero")
        etree.SubElement(ender, "xBairro").text = dest.get("bairro")
        etree.SubElement(ender, "cMun").text = str(dest.get("cod_municipio") or "9999999")
        etree.SubElement(ender, "xMun").text = dest.get("municipio")
        etree.SubElement(ender, "UF").text = dest.get("uf")
        etree.SubElement(ender, "CEP").text = dest.get("cep")

    # --------------------------------------------------------------
    def _det(self, root, itens):
        for i, item in enumerate(itens, start=1):
            det = etree.SubElement(root, "det", nItem=str(i))
            prod = etree.SubElement(det, "prod")

            quantidade = float(item.get("quantidade", 0) or 0)
            unit = float(item.get("valor_unit", 0) or 0)
            desconto = float(item.get("desconto", 0) or 0)
            vprod = quantidade * unit

            etree.SubElement(prod, "cProd").text = item.get("codigo")
            etree.SubElement(prod, "xProd").text = item.get("descricao")
            etree.SubElement(prod, "NCM").text = item.get("ncm")
            etree.SubElement(prod, "CFOP").text = item.get("cfop")
            etree.SubElement(prod, "uCom").text = item.get("unidade")
            etree.SubElement(prod, "qCom").text = f"{quantidade:.4f}"
            etree.SubElement(prod, "vUnCom").text = f"{unit:.2f}"
            etree.SubElement(prod, "vProd").text = f"{vprod:.2f}"
            if desconto > 0:
                etree.SubElement(prod, "vDesc").text = f"{desconto:.2f}"

    # --------------------------------------------------------------
    def _total(self, root, dto):
        total = etree.SubElement(root, "total")
        icms = etree.SubElement(total, "ICMSTot")

        vprod = 0.0
        vdesc = 0.0
        for it in dto["itens"]:
            q = float(it.get("quantidade", 0) or 0)
            u = float(it.get("valor_unit", 0) or 0)
            d = float(it.get("desconto", 0) or 0)
            vprod += (q * u)
            vdesc += d

        vnf = vprod - vdesc

        etree.SubElement(icms, "vBC").text = "0.00"
        etree.SubElement(icms, "vICMS").text = "0.00"
        etree.SubElement(icms, "vProd").text = f"{vprod:.2f}"
        etree.SubElement(icms, "vDesc").text = f"{vdesc:.2f}"
        etree.SubElement(icms, "vNF").text = f"{vnf:.2f}"

    # --------------------------------------------------------------
    def _pag(self, root, dto):
        pag = etree.SubElement(root, "pag")
        det = etree.SubElement(pag, "detPag")
        tpag = str(dto.get("tpag") or "01")
        etree.SubElement(det, "tPag").text = tpag
        # vPag: usa vNF calculado no _total
        vprod = 0.0
        vdesc = 0.0
        for it in dto["itens"]:
            q = float(it.get("quantidade", 0) or 0)
            u = float(it.get("valor_unit", 0) or 0)
            d = float(it.get("desconto", 0) or 0)
            vprod += (q * u)
            vdesc += d
        vnf = vprod - vdesc
        etree.SubElement(det, "vPag").text = f"{vnf:.2f}"

    # --------------------------------------------------------------
    def _resp_tecnico(self, root):
        r = etree.SubElement(root, "infRespTec")
        etree.SubElement(r, "CNPJ").text = "46123456000199"
        etree.SubElement(r, "xContato").text = "SPS Sistemas"
        etree.SubElement(r, "email").text = "suporte@mobile-sps.site"

    # --------------------------------------------------------------
    def _uf_to_cuf(self, uf):
        tabela = {
            "PR": "41",
            "SP": "35",
            "SC": "42",
            "RS": "43",
            "MG": "31",
        }
        return tabela.get(uf, "00")
