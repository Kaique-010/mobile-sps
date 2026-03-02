from ..dominio.dto import NotaFiscalDTO
from Pedidos.models import PedidoVenda


class PedidoNFeBuilder:

    def __init__(self, pedido: PedidoVenda, database=None, **kwargs):
        self.pedido = pedido
        self.database = database or pedido._state.db or 'default'
        self.pedido._state.db = self.database
        self.context = kwargs

    # -------------------------------------------------------------------
    # MÉTODO PRINCIPAL
    # -------------------------------------------------------------------
    def build(self):
        from datetime import date
        
        return NotaFiscalDTO(
            empresa=self.context.get('empresa', self.pedido.pedi_empr),
            filial=self.context.get('filial', self.pedido.pedi_fili),
            modelo=self.context.get('modelo', '55'),
            serie=self.context.get('serie', '1'),
            numero=self.context.get('numero', 0),
            data_emissao=self.context.get('data_emissao', str(date.today())),
            data_saida=self.context.get('data_saida', None),
            tipo_operacao=self.context.get('tipo_operacao', 1),
            finalidade=self.context.get('finalidade', 1),
            ambiente=self.context.get('ambiente', 2),
            
            emitente=self._emitente(),
            destinatario=self._destinatario(),
            itens=self._itens(),
        ).model_dump()

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
            if self.pedido.cliente:
                return self.pedido.cliente.enti_uf or ""
        except:
            pass
            
        # Se for NFC-e sem cliente, assume mesma UF da origem (filial)
        if str(self.context.get('modelo')) == '65':
            return self._uf_origem()
            
        return ""

    # -------------------------------------------------------------------
    # EMITENTE = FILIAL
    # -------------------------------------------------------------------
    def _emitente(self):
        from Licencas.models import Filiais
        from django.db import connection
        
        f = Filiais.objects.using(self.database).defer('empr_cert_digi').filter(
            empr_empr=self.pedido.pedi_empr,
            empr_codi=self.pedido.pedi_fili
        ).first()

        if not f:
            raise Exception("Filial não encontrada para o pedido.")

        return {
            "cnpj": f.empr_docu or "",
            "razao": f.empr_nome or "",
            "fantasia": f.empr_fant or f.empr_nome or "",
            "ie": f.empr_insc_esta or "",
            "regime_trib": str(f.empr_regi_trib or "3"),
            "logradouro": f.empr_ende or "",
            "numero": f.empr_nume or "",
            "bairro": f.empr_bair or "",
            "municipio": f.empr_cida or "",
            "cod_municipio": str(getattr(f, 'empr_codi_cida', '') or ''),
            "uf": f.empr_esta or "",
            "cep": f.empr_cep or "",
        }

    # -------------------------------------------------------------------
    # DESTINATÁRIO = ENTIDADES
    # -------------------------------------------------------------------
    def _destinatario(self):
        c = self.pedido.cliente
        if not c:
            # Se for NFC-e, permite sem cliente (consumidor final)
            if str(self.context.get('modelo')) == '65':
                # Pega a UF da filial/origem como padrão
                uf_dest = (c.enti_esta or "").strip()
                if not uf_dest:
                    # Fallback: use filial's UF for same-state sales, or raise a clear error
                    uf_dest = self._uf_origem()  # or raise Exception("Cliente sem UF cadastrada.")

                doc = c.enti_cnpj if c.enti_cnpj else c.enti_cpf
                ind_ie = "1"
                ie = c.enti_insc_esta
                if not ie or ie.upper() == "ISENTO":
                    ind_ie = "2" if ie and ie.upper() == "ISENTO" else "9"
                
                
                return {
                    "documento": "",
                    "nome": "",
                    "ie": "",
                    "ind_ie": "9",
                    "logradouro": "",
                    "numero": "",
                    "bairro": "",
                    "municipio": "",
                    "cod_municipio": "",
                    "uf": uf,
                    "cep": "",
                }
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

        qs = self.pedido.itens
        if self.database:
            qs = qs.using(self.database)

        for item in qs:  # já retorna o queryset custom
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