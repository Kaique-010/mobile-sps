class FiscalEngine:

    def __init__(self, empresa, operacao, cfop):
        self.empresa = empresa
        self.operacao = operacao
        self.cfop = cfop

    def calcular(self, base_calculo):

        resultado = {}

        # 1️⃣ ICMS Próprio
        if self.cfop.cfop_exig_icms:
            icms = ICMSService(self.empresa, self.operacao).calcular(
                base_calculo, self.cfop
            )
            resultado["icms"] = icms
        else:
            icms = None

        # 2️⃣ ST
        if self.cfop.cfop_gera_st:
            st = STService(self.empresa, self.operacao).calcular(
                base_calculo,
                icms_valor=icms["valor"] if icms else 0,
                cfop=self.cfop
            )
            resultado["st"] = st

        # 3️⃣ DIFAL
        if self.cfop.cfop_gera_difal:
            difal = DIFALService(self.empresa, self.operacao).calcular(
                base_calculo,
                icms_origem=icms["valor"] if icms else 0
            )
            resultado["difal"] = difal

        return resultado