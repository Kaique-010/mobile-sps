from .dto import NotaFiscalDTO, EmitenteDTO, DestinatarioDTO, ItemDTO
from ..models import Nota
from Licencas.models import Filiais


class NotaBuilder:
    def __init__(self, nota: Nota, database: str | None = None):
        self.nota = nota
        self.database = database or nota._state.db
        self.filial = Filiais.objects.using(self.database).get(empr_empr=nota.empresa, empr_codi=nota.filial)
        self.dest = nota.destinatario

    # -------------------------------
    # EMITENTE (FILIAL)
    # -------------------------------
    def build_emitente(self):
        f = self.filial
        return EmitenteDTO(
            cnpj=f.empr_docu,
            razao=f.empr_nome,
            fantasia=f.empr_fant or f.empr_nome,
            ie=f.empr_insc_esta or "",
            regime_trib=f.empr_regi_trib,

            logradouro=f.empr_ende,
            numero=f.empr_nume,
            bairro=f.empr_bair,
            municipio=f.empr_cida,
            cod_municipio=f.empr_codi_cida or "",
            uf=f.empr_esta,
            cep=f.empr_cep,
        )

    # -------------------------------
    # DESTINATÁRIO
    # -------------------------------
    def build_destinatario(self):
        d = self.dest

        doc = d.enti_cnpj or d.enti_cpf
        if d.enti_cnpj:
            ind_ie = "1" if d.enti_insc_esta else "2"
        else:
            ind_ie = "9"

        return DestinatarioDTO(
            documento=doc,
            nome=d.enti_nome or "",
            ie=d.enti_insc_esta or "",
            ind_ie=ind_ie,

            logradouro=d.enti_ende or "",
            numero=d.enti_nume or "",
            bairro="",
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

        for it in self.nota.itens.all():
            p = it.produto
            imp = it.impostos if hasattr(it, "impostos") else None

            itens.append(ItemDTO(
                codigo=p.prod_codi,
                descricao=p.prod_nome,
                unidade=p.prod_unme.unid_codi,

                quantidade=it.quantidade,
                valor_unit=it.unitario,
                desconto=it.desconto,

                ncm=it.ncm,
                cest=it.cest,
                cfop=it.cfop,

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
    # NOTA FISCAL DTO
    # -------------------------------
    def build(self):
        n = self.nota

        transporte = getattr(n, "transporte", None)
        frete_modalidade = transporte.modalidade_frete if transporte else None
        placa = transporte.placa_veiculo if transporte else None
        uf_veic = transporte.uf_veiculo if transporte else None

        return NotaFiscalDTO(
            empresa=n.empresa,
            filial=n.filial,

            modelo=n.modelo,
            serie=n.serie,
            numero=n.numero,

            data_emissao=str(n.data_emissao),
            data_saida=str(n.data_saida) if n.data_saida else None,
            tipo_operacao=n.tipo_operacao,
            finalidade=n.finalidade,
            ambiente=n.ambiente,

            emitente=self.build_emitente(),
            destinatario=self.build_destinatario(),
            itens=self.build_itens(),

            modalidade_frete=frete_modalidade,
            placa=placa,
            uf_veiculo=uf_veic,
        )
