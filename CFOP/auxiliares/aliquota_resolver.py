from decimal import Decimal


class AliquotaResolver:

    REGIME_SIMPLES = {"1", "2", "4", "MEI", "SIMPLES"}

    def _d(self, v):
        if v is None:
            return None
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v.quantize(Decimal("0.01"))

    def _get(self, obj, *attrs):
        for attr in attrs:
            if not attr:
                continue
            if hasattr(obj, attr):
                return getattr(obj, attr)
        return None

    def resolver(self, ncm_aliquota, regime):

        if not ncm_aliquota:
            return {
                "ipi": None,
                "pis": None,
                "cofins": None,
                "cbs": None,
                "ibs": None
            }

        is_simples = str(regime) in self.REGIME_SIMPLES

        ipi = self._get(ncm_aliquota, "aliq_ipi", "ipi", "nali_aliq_ipi")
        pis = self._get(ncm_aliquota, "aliq_pis", "pis", "nali_aliq_pis")
        cofins = self._get(ncm_aliquota, "aliq_cofins", "cofins", "nali_aliq_cofins")
        cbs = self._get(ncm_aliquota, "aliq_cbs", "cbs", "nali_aliq_cbs")
        ibs = self._get(ncm_aliquota, "aliq_ibs", "ibs", "nali_aliq_ibs")

        pis_sn = self._get(ncm_aliquota, "pis_sn", "aliq_pis_sn")
        cofins_sn = self._get(ncm_aliquota, "cofins_sn", "aliq_cofins_sn")

        return {
            "ipi": self._d(ipi),
            "pis": self._d(pis_sn if (is_simples and pis_sn is not None) else pis),
            "cofins": self._d(cofins_sn if (is_simples and cofins_sn is not None) else cofins),
            "cbs": self._d(cbs),
            "ibs": self._d(ibs),
        }
