from decimal import Decimal
import datetime

from pynfe.entidades.emitente import Emitente
from pynfe.entidades.cliente import Cliente
from pynfe.entidades.notafiscal import NotaFiscal
from pynfe.utils.flags import CODIGO_BRASIL


def construir_nfe_pynfe(dto):
    homolog_text = 'NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL' if int(dto.ambiente) == 2 else None

    emitente = Emitente(
        razao_social=homolog_text or dto.emitente.razao,
        nome_fantasia=homolog_text or dto.emitente.fantasia,
        cnpj=dto.emitente.cnpj,
        codigo_de_regime_tributario=str(dto.emitente.regime_trib or "1"),
        inscricao_estadual=(dto.emitente.ie or "")[:14],
        inscricao_municipal="",
        cnae_fiscal="",
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
        inscricao_estadual=dto.destinatario.ie or "",
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
    )

    for item in dto.itens:
        qtd = Decimal(str(item.quantidade))
        vunit = Decimal(str(item.valor_unit))
        vtotal = Decimal(str((item.quantidade or 0) * (item.valor_unit or 0)))

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
            icms_modalidade="102" if str(dto.emitente.regime_trib) == "1" else None,
            icms_origem=0,
            icms_csosn="400" if str(dto.emitente.regime_trib) == "1" else None,
            pis_modalidade="07",
            cofins_modalidade="07",
            valor_tributos_aprox=None,
        )

    return nota_fiscal
