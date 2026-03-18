from .dto import NotaFiscalDTO, EmitenteDTO, DestinatarioDTO, ItemDTO, ResponsavelTecnicoDTO
from ..models import Nota
from Licencas.models import Filiais
from Produtos.models import Produtos
import re


class NotaBuilder:
    def __init__(self, nota: Nota, database: str | None = None):
        self.nota = nota
        self.database = database or nota._state.db
        self.filial = Filiais.objects.using(self.database).defer('empr_cert_digi').get(empr_empr=nota.empresa, empr_codi=nota.filial)
        self.dest = nota.destinatario

    def _limpar_inscricao_estadual(self, valor):
        s = str(valor or "").strip()
        if not s:
            return ""
        if "ISENTO" in s.upper():
            return "ISENTO"
        somente_digitos = re.sub(r"\D", "", s)
        return somente_digitos[:14]

    def _somente_digitos(self, valor, max_len=None):
        s = re.sub(r"\D", "", str(valor or ""))
        if max_len is not None:
            s = s[:max_len]
        return s

    def _limpar_ncm(self, valor):
        return self._somente_digitos(valor, 8)

    def _limpar_cfop(self, valor):
        return self._somente_digitos(valor, 4)

    def _limpar_cest(self, valor):
        return self._somente_digitos(valor, 7)

    # -------------------------------
    # EMITENTE (FILIAL)
    # -------------------------------
    def build_emitente(self):
        f = self.filial
        regime = str(getattr(f, "empr_regi_trib", "") or "1").strip()

        cpf = None
        if regime == "5":
            cpf = self._somente_digitos(f.empr_docu, 11)
            if cpf:
                cpf = cpf.zfill(11)
            cnpj = (cpf or "").zfill(14)
        else:
            cnpj = self._somente_digitos(f.empr_docu, 14)
            if cnpj:
                cnpj = cnpj.zfill(14)

        return EmitenteDTO(
            cnpj=cnpj or "",
            cpf=cpf,
            razao=f.empr_nome,
            fantasia=f.empr_fant or f.empr_nome,
            ie=self._limpar_inscricao_estadual(f.empr_insc_esta),
            regime_trib=regime,
            cnae=self._somente_digitos(f.empr_cnae),
            inscricao_municipal=self._somente_digitos(f.empr_insc_muni),

            logradouro=f.empr_ende,
            numero=f.empr_nume,
            bairro=f.empr_bair,
            municipio=f.empr_cida,
            cod_municipio=f.empr_codi_cida or "",
            uf=f.empr_esta,
            cep=f.empr_cep,
        )
    
    def build_emitente_produtor_rural_pessoa_fisica_ou_juridica(self):
        return self.build_emitente()

    # -------------------------------
    # DESTINATÁRIO
    # -------------------------------
    def build_destinatario(self):
        d = self.dest

        raw_doc = d.enti_cnpj or d.enti_cpf
        doc = self._somente_digitos(raw_doc)
        
        if len(doc) > 11:
            doc = doc.zfill(14)
        elif doc:
            doc = doc.zfill(11)

        raw_ie = self._somente_digitos(d.enti_insc_esta)
        # Se tem CNPJ e IE válida (pelo menos 2 dígitos)
        if len(doc) == 14 and raw_ie and len(raw_ie) > 1:
            ind_ie = "1"
            ie_val = raw_ie[:14]
        else:
            ind_ie = "9"
            ie_val = None

        return DestinatarioDTO(
            documento=doc,
            nome=d.enti_nome or "",
            ie=ie_val,
            ind_ie=ind_ie,

            logradouro=d.enti_ende or "",
            numero=d.enti_nume or "",
            bairro=(d.enti_bair or "").strip() or "CENTRO",
            municipio=d.enti_cida or "",
            cod_municipio=str(getattr(d, "enti_codi_cida", "") or ""),
            uf=d.enti_esta or "",
            cep=d.enti_cep or "",
        )

    # -------------------------------
    # ITENS
    # -------------------------------
    def build_itens(self):
        itens = []
        
        # Ensure we use the correct database for related manager
        itens_qs = self.nota.itens.all()
        if self.database:
             itens_qs = itens_qs.using(self.database)

        for it in itens_qs:
            prod_qs = Produtos.objects.using(self.database).filter(prod_codi=it.produto_id)
            empresa = getattr(self.nota, "empresa", None)
            if empresa is not None:
                prod_qs = prod_qs.filter(prod_empr=str(empresa))
            p = prod_qs.first()
            if not p:
                p = Produtos.objects.using(self.database).filter(prod_codi=it.produto_id).first()
            if not p:
                raise Exception(f"Produto {it.produto_id} não encontrado para empresa {empresa}.")

            imp = it.impostos if hasattr(it, "impostos") else None

            itens.append(ItemDTO(
                codigo=p.prod_codi,
                descricao=p.prod_nome,
                unidade=p.prod_unme.unid_codi,

                quantidade=it.quantidade,
                valor_unit=it.unitario,
                desconto=it.desconto,

                ncm=self._limpar_ncm(it.ncm),
                cest=self._limpar_cest(it.cest),
                cfop=self._limpar_cfop(it.cfop),

                cst_icms=it.cst_icms,
                cst_pis=it.cst_pis,
                cst_cofins=it.cst_cofins,

                base_icms=imp.icms_base if imp else None,
                valor_icms=imp.icms_valor if imp else None,
                aliq_icms=imp.icms_aliquota if imp else None,

                base_icms_st=imp.icms_st_base if imp else None,
                valor_icms_st=imp.icms_st_valor if imp else None,
                aliq_icms_st=imp.icms_st_aliquota if imp else None,
                mva_st=imp.icms_mva_st if imp else None,
                
                valor_frete=it.valor_frete,
                valor_seguro=it.valor_seguro,
                valor_outras_despesas=it.valor_outras_despesas,

                base_ipi=imp.ipi_base if imp else None,
                aliq_ipi=imp.ipi_aliquota if imp else None,
                valor_ipi=imp.ipi_valor if imp else None,

                base_pis=imp.pis_base if imp else None,
                aliq_pis=imp.pis_aliquota if imp else None,
                valor_pis=imp.pis_valor if imp else None,

                base_cofins=imp.cofins_base if imp else None,
                aliq_cofins=imp.cofins_aliquota if imp else None,
                valor_cofins=imp.cofins_valor if imp else None,

                base_ibs=imp.ibs_base if imp else None,
                aliq_ibs=imp.ibs_aliquota if imp else None,
                valor_ibs=imp.ibs_valor if imp else None,

                base_cbs=imp.cbs_base if imp else None,
                aliq_cbs=imp.cbs_aliquota if imp else None,
                valor_cbs=imp.cbs_valor if imp else None,

                valor_fcp=imp.fcp_valor if imp else None,
            ))

        return itens

    # -------------------------------
    # RESPONSÁVEL TÉCNICO
    # -------------------------------
    def build_responsavel_tecnico(self):
        from decouple import config
        
        f = self.filial
        fone = self._somente_digitos(f.empr_fone)
        if not fone:
            fone = "4232236164"  # Default Spartacus Phone
            
        # Tenta ler do .env (Configuração global da Software House)
        id_csrt = config('CSRT_ID', default=None)
        csrt_key = config('CSRT_KEY', default=None) 

        uf_emit = str(getattr(f, "empr_esta", "") or "").strip().upper()
        tp_amb = int(getattr(self.nota, "ambiente", None) or 2)
        if not id_csrt:
            if tp_amb == 1:
                id_csrt = config("CSRT_ID_PRODUCAO", default=None)
            else:
                id_csrt = config("CSRT_ID_HOMOLOGACAO", default=None)
        if not csrt_key:
            if tp_amb == 1:
                csrt_key = config("CSRT_KEY_PRODUCAO", default=None)
            else:
                csrt_key = config("CSRT_KEY_HOMOLOGACAO", default=None)

        if uf_emit == "PR":
            if tp_amb == 1:
                if not csrt_key:
                    csrt_key = "R94XGP4QKW4DFEUD215P5BADXKQV0UDQIQZQ"
                if not id_csrt:
                    id_csrt = "3"
            else:
                if not csrt_key:
                    csrt_key = "TBPHFPLCMUIB4K4CGY3SJW1RE8YWQWFQ4D56"
                if not id_csrt:
                    id_csrt = "1"
        
        # Se não tiver no .env, tenta verificar se existe no model Filiais (futuro)
        if not id_csrt and hasattr(f, 'empr_csrt_id'):
            id_csrt = getattr(f, 'empr_csrt_id')
            
        if not csrt_key and hasattr(f, 'empr_csrt_key'):
            csrt_key = getattr(f, 'empr_csrt_key')
            
        return ResponsavelTecnicoDTO(
            cnpj="20702018000142",
            contato="DANIEL DIAS DE ALMEIDA",
            email="spartacus@spartacus.com.br",
            fone=fone,
            id_csrt=id_csrt,
            hash_csrt=None, # Será calculado no SefazAdapter se tiver key
            csrt_key=csrt_key
        )

    # -------------------------------
    # NOTA FISCAL DTO
    # -------------------------------
    def build(self):
        n = self.nota

        transporte = getattr(n, "transporte", None)
        frete_modalidade = transporte.modalidade_frete if transporte else None
        placa = transporte.placa_veiculo if transporte else None
        uf_veic = transporte.uf_veiculo if transporte else None

        # Ajuste para NFC-e (modelo 65) que exige hora com tolerância de 5 minutos
        # Como o model Nota usa DateField, a hora é perdida.
        # Se for NFC-e e a data de emissão for hoje, usamos a hora atual.
        data_emissao_str = str(n.data_emissao)
        if str(n.modelo) == '65':
            from django.utils import timezone
            agora = timezone.now()
            # Se a data salva no banco for igual à data de hoje, assume-se que é uma emissão imediata
            if n.data_emissao == agora.date():
                data_emissao_str = agora.isoformat()

        return NotaFiscalDTO(
            empresa=n.empresa,
            filial=n.filial,

            modelo=n.modelo,
            serie=n.serie,
            numero=n.numero,
            
            responsavel_tecnico=self.build_responsavel_tecnico(),

            data_emissao=data_emissao_str,
            data_saida=str(n.data_saida) if n.data_saida else None,
            tipo_operacao=n.tipo_operacao,
            finalidade=n.finalidade,
            ambiente=n.ambiente,
            chave_referenciada=str(getattr(n, "chave_referenciada", "") or "").strip() or None,

            emitente=self.build_emitente(),
            destinatario=self.build_destinatario(),
            itens=self.build_itens(),

            modalidade_frete=frete_modalidade,
            placa=placa,
            uf_veiculo=uf_veic,
        )
