from decimal import Decimal
from typing import Dict, Optional
import logging
from Licencas.models import Filiais

logger = logging.getLogger(__name__)

def get_empresa_uf_origem(empresa_id, filial_id=None, banco=None):
    qs = Filiais.objects
    if banco:
        qs = qs.using(banco)
    f = qs.filter(empr_empr=empresa_id, empr_codi=filial_id).first()
    return getattr(f, "empr_esta", "") if f else ""

def get_regime(empresa_id, filial_id=None, banco=None):
    qs = Filiais.objects
    if banco:
        qs = qs.using(banco)
    f = qs.filter(empr_empr=empresa_id, empr_codi=filial_id).first()
    return getattr(f, "empr_regi_trib", "") if f else ""

class ResolverAliquotaPorRegime:
    """
    Responsável por resolver as alíquotas base considerando o regime tributário.
    Prepara o terreno para a reforma tributária (IBS/CBS).
    """
    
    REGIME_SIMPLES = ["1", "2"] # 1=Simples, 2=Simples Excesso
    REGIME_NORMAL = ["3"]
    
    def resolver(self, ncm_aliquota: object, regime: str) -> Dict[str, Optional[Decimal]]:
        """
        Retorna dicionário de alíquotas base ajustado pelo regime.
        """
        defaults = {
            "ipi": None, "pis": None, "cofins": None, 
            "cbs": None, "ibs": None
        }
        
        # Helper para decimal
        def _d(v):
            if v is None: return None
            return Decimal(str(v))

        if not ncm_aliquota:
            return defaults

        # Alíquotas base do NCM (IBPT/Tabela TiPi)
        aliqs = {
            "ipi": _d(getattr(ncm_aliquota, "aliq_ipi", None)),
            "pis": _d(getattr(ncm_aliquota, "aliq_pis", None)),
            "cofins": _d(getattr(ncm_aliquota, "aliq_cofins", None)),
            "cbs": _d(getattr(ncm_aliquota, "aliq_cbs", None)),
            "ibs": _d(getattr(ncm_aliquota, "aliq_ibs", None)),
        }
        
        # Log de Auditoria
        logger.debug(
            f"Resolvendo alíquotas para Regime={regime}. "
            f"Base NCM: IPI={aliqs['ipi']}, PIS={aliqs['pis']}, COFINS={aliqs['cofins']}"
        )
        
        # Lógica Específica por Regime
        if str(regime) in self.REGIME_SIMPLES:
            # Futuramente: lógica de transição para IBS/CBS no Simples
            # Por enquanto mantém as alíquotas base do cadastro (que podem ser usadas para cálculo de crédito ou info complementar)
            pass
            
        return aliqs
