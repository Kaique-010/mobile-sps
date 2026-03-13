from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Any, Optional

from CFOP.models import CFOP, Ncm
from Produtos.models import Produtos


@dataclass

class BaseFiscal: 
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
    banco: Optional[str]

    regime: str
    uf_origem: str
    uf_destino: str

    produto: Produtos

    cfop: Optional[CFOP] = None
    ncm: Optional[Ncm] = None

    # Overrides fiscais
    override: Dict[str, Any] = field(default_factory=dict)
    overrides_dif: Dict[str, Any] = field(default_factory=dict)
    overrides_sn: Dict[str, Any] = field(default_factory=dict)

    fiscal_padrao: Optional[Any] = None

    # Dados fiscais resolvidos
    aliquotas_base: Dict[str, Decimal | None] = field(default_factory=dict)
    icms_data: Dict[str, Decimal | None] = field(default_factory=dict)