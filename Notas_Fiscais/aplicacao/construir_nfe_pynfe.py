from decimal import Decimal
import datetime
import random
import re

from pynfe.entidades.emitente import Emitente
from pynfe.entidades.cliente import Cliente
from pynfe.entidades.notafiscal import NotaFiscal
from pynfe.utils.flags import CODIGO_BRASIL


def _limpar_inscricao_estadual(valor):
    s = str(valor or "").strip()
    if not s:
        return ""
    if "ISENTO" in s.upper():
        return "ISENTO"
    somente_digitos = re.sub(r"\D", "", s)
    return somente_digitos[:14]

def _normalizar_crt(regime_trib):
    r = str(regime_trib or "").strip()

    if r in ("1", "2", "3"):
        return r


    if r in ("4", "5"):
        return "3"

    return "3"

def construir_nfe_pynfe(dto):
    homolog_text = 'NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL' if int(dto.ambiente) == 2 else None
    crt = _normalizar_crt(getattr(dto.emitente, "regime_trib", None))

    emitente = Emitente(
        razao_social=homolog_text or dto.emitente.razao,
        nome_fantasia=homolog_text or dto.emitente.fantasia,
        cnpj=dto.emitente.cnpj,
        codigo_de_regime_tributario=crt,
        inscricao_estadual=_limpar_inscricao_estadual(dto.emitente.ie),
        inscricao_municipal=dto.emitente.inscricao_municipal or "",
        cnae_fiscal=dto.emitente.cnae or "",
        endereco_logradouro=dto.emitente.logradouro,
        endereco_numero=dto.emitente.numero,
        endereco_bairro=dto.emitente.bairro,
        endereco_municipio=dto.emitente.municipio,
        endereco_uf=dto.emitente.uf,
        endereco_cep=dto.emitente.cep,
        endereco_pais=CODIGO_BRASIL,
    )

    tipo_doc = "CNPJ" if len(dto.destinatario.documento or "") == 14 else "CPF"
    cliente = Cliente(
        razao_social=homolog_text or dto.destinatario.nome,
        tipo_documento=tipo_doc,
        email="",
        numero_documento=dto.destinatario.documento,
        indicador_ie=int(dto.destinatario.ind_ie or "9"),
        inscricao_estadual=_limpar_inscricao_estadual(dto.destinatario.ie),
        endereco_logradouro=dto.destinatario.logradouro,
        endereco_numero=dto.destinatario.numero,
        endereco_complemento="",
        endereco_bairro=dto.destinatario.bairro,
        endereco_municipio=dto.destinatario.municipio,
        endereco_uf=dto.destinatario.uf,
        endereco_cep=dto.destinatario.cep,
        endereco_pais=CODIGO_BRASIL,
        endereco_telefone="",
    )

    data_emissao = datetime.datetime.fromisoformat(str(dto.data_emissao))
    data_saida = (
        datetime.datetime.fromisoformat(str(dto.data_saida)) if dto.data_saida else data_emissao
    )

    nota_fiscal = NotaFiscal(
        emitente=emitente,
        cliente=cliente,
        uf=dto.emitente.uf.upper(),
        natureza_operacao="VENDA",
        forma_pagamento=0,
        tipo_pagamento=1,
        modelo=int(dto.modelo),
        serie=str(dto.serie),
        numero_nf=str(dto.numero),
        data_emissao=data_emissao,
        data_saida_entrada=data_saida,
        tipo_documento=int(dto.tipo_operacao),
        municipio=str(dto.emitente.cod_municipio or ""),
        tipo_impressao_danfe=1 if dto.modelo == "55" else 4,
        forma_emissao="1",
        cliente_final=1,
        indicador_destino=1,
        indicador_presencial=1,
        finalidade_emissao=str(dto.finalidade),
        processo_emissao="0",
        transporte_modalidade_frete=dto.modalidade_frete or 9,
        informacoes_adicionais_interesse_fisco="",
        totais_tributos_aproximado=None,
        codigo_numerico=str(random.randint(10000000, 99999999)), # Gera cNF aleatório para evitar Rejeição 656 (Consumo Indevido)
    )
    emitente_cpf = str(getattr(dto.emitente, "cpf", "") or "").strip()
    if emitente_cpf:
        nota_fiscal._emitente_cpf = emitente_cpf
    
    # Armazena dados do responsável técnico para injeção posterior no XML (SefazAdapter)
    if dto.responsavel_tecnico:
        nota_fiscal._responsavel_tecnico = dto.responsavel_tecnico
    chave_ref = str(getattr(dto, "chave_referenciada", "") or "").strip()
    if chave_ref and len(chave_ref) == 44 and chave_ref.isdigit():
        nota_fiscal._chave_referenciada = chave_ref

    for item in dto.itens:
        cst_icms_raw = str(getattr(item, "cst_icms", "") or "").strip()
        if crt == "1":
            csosn = cst_icms_raw if len(cst_icms_raw) == 3 else "102"
            icms_modalidade = _obter_modalidade_csosn(csosn)
            icms_csosn = csosn
        else:
            cst = cst_icms_raw if len(cst_icms_raw) == 2 else "00"
            icms_modalidade = cst or "00"
            icms_csosn = None

        qtd = Decimal(str(item.quantidade))
        vunit = Decimal(str(item.valor_unit))
        vtotal = Decimal(str((item.quantidade or 0) * (item.valor_unit or 0)))
        icms_base = Decimal(str(getattr(item, "base_icms", None) or 0))
        icms_aliq = Decimal(str(getattr(item, "aliq_icms", None) or 0))
        icms_valor = Decimal(str(getattr(item, "valor_icms", None) or 0))
        icms_st_base = Decimal(str(getattr(item, "base_icms_st", None) or 0))
        icms_st_aliq = Decimal(str(getattr(item, "aliq_icms_st", None) or 0))
        icms_st_valor = Decimal(str(getattr(item, "valor_icms_st", None) or 0))
        mva_st = Decimal(str(getattr(item, "mva_st", None) or 0))
        fcp_valor = Decimal(str(getattr(item, "valor_fcp", None) or 0))

        nota_fiscal.adicionar_produto_servico(
            codigo=str(item.codigo),
            descricao=item.descricao,
            ncm=item.ncm or "99999999",
            cfop=item.cfop or "5102",
            unidade_comercial=item.unidade,
            ean="SEM GTIN",
            ean_tributavel="SEM GTIN",
            quantidade_comercial=qtd,
            valor_unitario_comercial=vunit,
            valor_total_bruto=vtotal,
            unidade_tributavel=item.unidade,
            quantidade_tributavel=qtd,
            valor_unitario_tributavel=vunit,
            ind_total=1,
            icms_modalidade=icms_modalidade,
            icms_origem=0,
            icms_csosn=icms_csosn,
            icms_modalidade_determinacao_bc=3,
            icms_valor_base_calculo=icms_base,
            icms_aliquota=icms_aliq,
            icms_valor=icms_valor,
            icms_st_modalidade_determinacao_bc=4,
            icms_st_percentual_adicional=mva_st,
            icms_st_percentual_reducao_bc=0,
            icms_st_valor_base_calculo=icms_st_base,
            icms_st_aliquota=icms_st_aliq,
            icms_st_valor=icms_st_valor,
            fcp_valor=fcp_valor,
            pis_modalidade=str(getattr(item, "cst_pis", None) or "07"),
            cofins_modalidade=str(getattr(item, "cst_cofins", None) or "07"),
            valor_tributos_aprox=None,
        )
        
        # Armazena dados de IBS/CBS para injeção posterior no XML (SefazAdapter)
        if not hasattr(nota_fiscal, '_itens_extra'):
            nota_fiscal._itens_extra = []
            
        nota_fiscal._itens_extra.append({
            'ibs': {
                'valor': item.valor_ibs, 
                'base': item.base_ibs, 
                'aliq': item.aliq_ibs
            },
            'cbs': {
                'valor': item.valor_cbs, 
                'base': item.base_cbs, 
                'aliq': item.aliq_cbs
            }
        })

    return nota_fiscal

def _obter_modalidade_csosn(csosn):
    if not csosn: return "102"
    c = str(csosn)
    if c in ["101"]: return "101"
    if c in ["102", "103", "300", "400"]: return "102"
    if c in ["201"]: return "201"
    if c in ["202", "203"]: return "202"
    if c in ["500"]: return "500"
    if c in ["900"]: return "900"
    return "102"
