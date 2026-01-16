from ..dominio.dto import NotaFiscalDTO
from Pedidos.models import PedidoVenda


class PedidoNFeBuilder:

    def __init__(self, pedido: PedidoVenda):
        self.pedido = pedido

    # -------------------------------------------------------------------
    # MÉTODO PRINCIPAL
    # -------------------------------------------------------------------
    def build(self):
        return NotaFiscalDTO(
            emitente=self._emitente(),
            destinatario=self._destinatario(),
            itens=self._itens(),
            totais=self._totais(),
            pagamentos=self._pagamentos(),
            tipo_operacao=1 if self.pedido.pedi_tipo_oper == "VENDA" else 0,
            cfop_padrao=self._resolve_cfop(),
            uf_origem=self._uf_origem(),
            uf_destino=self._uf_destino(),
        ).to_dict()

    # -------------------------------------------------------------------
    # UF DE ORIGEM (FILIAL)
    # -------------------------------------------------------------------
    def _uf_origem(self):
        return self.pedido.get_uf_origem() or ""

    # -------------------------------------------------------------------
    # UF DESTINO (CLIENTE)
    # -------------------------------------------------------------------
    def _uf_destino(self):
        try:
            return self.pedido.cliente.enti_uf or ""
        except:
            return ""

    # -------------------------------------------------------------------
    # EMITENTE = FILIAL
    # -------------------------------------------------------------------
    def _emitente(self):
        from Licencas.models import Filiais
        
        f = Filiais.objects.filter(
            empr_empr=self.pedido.pedi_empr,
            empr_codi=self.pedido.pedi_fili
        ).first()

        if not f:
            raise Exception("Filial não encontrada para o pedido.")

        return {
            "cnpj": f.empr_docu,
            "razao": f.empr_nome,
            "fantasia": f.empr_fant or f.empr_nome,
            "ie": f.empr_insc_esta or "",
            "regime_trib": str(f.empr_regi_trib or "3"),
            "logradouro": f.empr_ende,
            "numero": f.empr_nume,
            "bairro": f.empr_bair,
            "municipio": f.empr_cida,
            "cod_municipio": str(getattr(f, 'empr_codi_cida', '') or ''),
            "uf": f.empr_esta,
            "cep": f.empr_cep,
        }

    # -------------------------------------------------------------------
    # DESTINATÁRIO = ENTIDADES
    # -------------------------------------------------------------------
    def _destinatario(self):
        c = self.pedido.cliente
        if not c:
            raise Exception("Cliente não encontrado no pedido.")

        doc = c.enti_cnpj if c.enti_cnpj else c.enti_cpf
        ind_ie = "1"
        ie = c.enti_insc_esta
        if not ie or ie.upper() == "ISENTO":
            ind_ie = "2" if ie and ie.upper() == "ISENTO" else "9"
        
        return {
            "documento": doc or "",
            "nome": c.enti_nome,
            "ie": ie,
            "ind_ie": ind_ie,
            "logradouro": c.enti_ende,
            "numero": c.enti_nume,
            "bairro": c.enti_bair,
            "municipio": c.enti_cida,
            "cod_municipio": str(getattr(c, 'enti_codi_cida', '') or ''),
            "uf": c.enti_esta,
            "cep": c.enti_cep,
        }

    # -------------------------------------------------------------------
    # ITENS = Itenspedidovenda + Produtos
    # -------------------------------------------------------------------
    def _itens(self):
        itens_dto = []

        for item in self.pedido.itens:  # já retorna o queryset custom
            p = item.produto  # Produtos

            if not p:
                raise Exception(f"Produto {item.iped_prod} não encontrado.")

            unidade = getattr(p.prod_unme, "unme_sigla", None)
            if not unidade:
                unidade = "UN"  # fallback

            itens_dto.append({
                "codigo": str(p.prod_codi),
                "descricao": p.prod_nome,
                "ncm": p.prod_ncm,
                "unidade": unidade,
                "cfop": self._resolve_cfop(),
                "quantidade": float(item.iped_quan or 0),
                "valor_unit": float(item.iped_unit or 0),
                "valor_total": float(item.iped_tota or 0),
                "desconto": float(item.iped_desc or 0),
                "cest": None,
                "cst_icms": "00",
                "cst_pis": "01",
                "cst_cofins": "01",
            })

        return itens_dto

    # -------------------------------------------------------------------
    # TOTAIS (valores REAIS do PedidoVenda)
    # -------------------------------------------------------------------
    def _totais(self):
        return {
            "valor_produtos": float(self.pedido.pedi_topr or 0),
            "valor_total": float(self.pedido.pedi_tota or 0),
            "desconto": float(self.pedido.pedi_desc or 0),
            "liquido": float(self.pedido.pedi_liqu or self.pedido.pedi_tota or 0),
        }

    # -------------------------------------------------------------------
    # PAGAMENTO (Forma de recebimento do pedido)
    # campo real → pedi_form_rece
    # -------------------------------------------------------------------
    def _pagamentos(self):
        return [{
            "forma": self.pedido.pedi_form_rece,  # já vem no formato '54', '51', '60', etc.
            "valor": float(self.pedido.pedi_tota or 0),
            "tipo": self.pedido.pedi_fina,  # à vista / a prazo / sem financeiro
        }]

    # -------------------------------------------------------------------
    # CFOP PADRÃO
    # (depois conectamos ao MapaCFOP real)
    # -------------------------------------------------------------------
    def _resolve_cfop(self):
        tipo = self.pedido.pedi_tipo_oper

        if tipo == "DEVOLUCAO_VENDA":
            return "1202"
        if tipo == "BONIFICACAO":
            return "5910"
        if tipo == "REMESSA":
            return "5915" 
        if tipo == "TRANSFERENCIA":
            return "5152"

        return "5102"  # venda padrão