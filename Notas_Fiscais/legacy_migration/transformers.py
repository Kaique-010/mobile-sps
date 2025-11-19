class NotaTransformer:

    @staticmethod
    def emitente(data):
        return {
            "empresa": data["empresa"],
            "filial": data["filial"],
            "cnpj": data["c02_cnpj"],
            "razao_social": data["c03_xnome"],
            "nome_fantasia": data["c04_xfant"],
            "logradouro": data["c06_xlgr"],
            "numero": data["c07_nro"],
            "bairro": data["c09_xbairro"],
            "codigo_municipio": data["c10_cmun"],
            "nome_municipio": data["c11_xmun"],
            "uf": data["c12_uf"],
            "cep": data["c13_cep"],
            "ie": data["c17_ie"],
        }

    @staticmethod
    def destinatario(data):
        return {
            "documento": data["e02_cnpj"] or data["e03_cpf"],
            "nome": data["e04_xnome"],
            "logradouro": data["e06_xlgr"],
            "numero": data["e07_nro"],
            "bairro": data["e09_xbairro"],
            "codigo_municipio": data["e10_cmun"],
            "nome_municipio": data["e11_xmun"],
            "uf": data["e12_uf"],
            "cep": data["e13_cep"],
            "email": data["e19_email"],
            "ie": data["e17_ie"],
        }

    @staticmethod
    def nota(data, emitente, destinatario):
        return {
            "empresa": data["empresa"],
            "filial": data["filial"],
            "modelo": data["b06_mod"],
            "serie": data["b07_serie"],
            "numero": data["b08_nnf"],
            "data_emissao": data["b09_demi"],
            "data_saida": data["b10_dsaient"],
            "tipo_operacao": data["b11_tpnf"],
            "finalidade": data["b25_finnfe"],
            "ambiente": data["b24_tpamb"],
            "status": data["status_nfe"] or 0,
            "chave_acesso": data["a03_id"],
            "protocolo_autorizacao": data["prot_nfe"],
            "emitente": emitente,
            "destinatario": destinatario,
        }

    @staticmethod
    def item(row):
        quantidade = row.get("i10_qcom") or row.get("qcom_orig") or 0
        unitario = row.get("i10a_vuncom") or row.get("vuncom_orig")
        total = row.get("i11_vprod") or row.get("vprod_orig")
        desconto = row.get("i17_vdesc") or row.get("vdesc_orig") or 0
        return {
            "produto_codigo": row.get("i02_cprod"),
            "quantidade": quantidade,
            "unitario": unitario if unitario is not None else (total or 0) / (quantidade or 1),
            "desconto": desconto,
            "cfop": str(row.get("i08_cfop") or ""),
            "ncm": row.get("i05_ncm") or "",
            "cest": row.get("i06_extipi"),
            "cst_icms": row.get("n12_cst") or row.get("n12a_csosn") or "",
            "cst_pis": row.get("q06_cst_pis") or "",
            "cst_cofins": row.get("s06_cst_cofins") or "",
            "total": total or 0,
        }

    @staticmethod
    def imposto(row):
        return {
            "icms_base": row.get("n15_vbc"),
            "icms_aliquota": row.get("n16_picms"),
            "icms_valor": row.get("n17_vicms"),
            "ipi_valor": row.get("o14_vipi"),
            "pis_valor": row.get("q09_vpis"),
            "cofins_valor": row.get("s11_vcofins"),
            "fcp_valor": row.get("vfcpufdest"),
            "ibs_base": None,
            "ibs_aliquota": None,
            "ibs_valor": None,
            "cbs_base": None,
            "cbs_aliquota": None,
            "cbs_valor": None,
        }