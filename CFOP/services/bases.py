from dataclasses import dataclass   
from decimal import Decimal
from typing import Dict, Any
from CFOP.models import CFOP, Ncm, Produtos


@dataclass
class BasesFiscal:
    raiz: Decimal
    icms: Decimal
    st: Decimal | None
    pis_cofins: Decimal
    cbs: Decimal
    ibs: Decimal


@dataclass
class FiscalContexto:
    empresa_id: int
    filial_id: int
    banco: str | None

    regime: str
    uf_origem: str
    uf_destino: str

    produto: Produtos
    cfop: CFOP | None = None
    ncm: Ncm | None = None
    
    # Cache de overrides e dados fiscais
    override: Dict[str, Any] = None
    overrides_dif: Dict[str, Any] = None
    overrides_sn: Dict[str, Any] = None
    fiscal_padrao: Any = None 
    aliquotas_base: Dict[str, Decimal | None] = None
    icms_data: Dict[str, Decimal | None] = None