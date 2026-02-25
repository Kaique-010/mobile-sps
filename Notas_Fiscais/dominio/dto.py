from pydantic import BaseModel
from decimal import Decimal
from typing import List, Optional


class EmitenteDTO(BaseModel):
    cnpj: str
    razao: str
    fantasia: str
    ie: str
    regime_trib: str
    logradouro: str
    numero: str
    bairro: str
    municipio: str
    cod_municipio: str
    uf: str
    cep: str


class DestinatarioDTO(BaseModel):
    documento: str
    nome: str
    ie: Optional[str]
    ind_ie: str
    logradouro: str
    numero: str
    bairro: str
    municipio: str
    cod_municipio: str
    uf: str
    cep: str


class ResponsavelTecnicoDTO(BaseModel):
    cnpj: str
    contato: str
    email: str
    fone: str
    id_csrt: Optional[str] = None
    hash_csrt: Optional[str] = None


class ItemDTO(BaseModel):
    codigo: str
    descricao: str
    unidade: str
    quantidade: Decimal
    valor_unit: Decimal
    desconto: Decimal
    ncm: str
    cest: Optional[str]
    cfop: str
    cst_icms: str
    cst_pis: str
    cst_cofins: str

    base_icms: Optional[Decimal] = None
    valor_icms: Optional[Decimal] = None
    aliq_icms: Optional[Decimal] = None
    
    base_icms_st: Optional[Decimal] = None
    valor_icms_st: Optional[Decimal] = None
    aliq_icms_st: Optional[Decimal] = None
    mva_st: Optional[Decimal] = None

    base_ipi: Optional[Decimal] = None
    aliq_ipi: Optional[Decimal] = None
    valor_ipi: Optional[Decimal] = None
    
    valor_frete: Optional[Decimal] = None
    valor_seguro: Optional[Decimal] = None
    valor_outras_despesas: Optional[Decimal] = None

    base_pis: Optional[Decimal] = None
    aliq_pis: Optional[Decimal] = None
    valor_pis: Optional[Decimal] = None

    base_cofins: Optional[Decimal] = None
    aliq_cofins: Optional[Decimal] = None
    valor_cofins: Optional[Decimal] = None
    
    base_ibs: Optional[Decimal] = None
    aliq_ibs: Optional[Decimal] = None
    valor_ibs: Optional[Decimal] = None

    base_cbs: Optional[Decimal] = None
    aliq_cbs: Optional[Decimal] = None
    valor_cbs: Optional[Decimal] = None

    valor_fcp: Optional[Decimal] = None


class NotaFiscalDTO(BaseModel):
    empresa: int
    filial: int

    modelo: str
    serie: str
    numero: int
    data_emissao: str
    data_saida: Optional[str]
    tipo_operacao: int
    finalidade: int
    ambiente: int

    emitente: EmitenteDTO
    destinatario: DestinatarioDTO
    responsavel_tecnico: Optional[ResponsavelTecnicoDTO] = None
    itens: List[ItemDTO]

    modalidade_frete: Optional[int] = None
    transportadora: Optional[DestinatarioDTO] = None
    placa: Optional[str] = None
    uf_veiculo: Optional[str] = None
