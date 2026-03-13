import logging
from Licencas.models import Filiais
from ..auxiliares.aliquota_resolver import AliquotaResolver

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
    REGIME_SIMPLES = AliquotaResolver.REGIME_SIMPLES

    def resolver(self, ncm_aliquota, regime):
        return AliquotaResolver().resolver(ncm_aliquota, regime)
