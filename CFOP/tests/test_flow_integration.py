from django.test import SimpleTestCase
from unittest.mock import MagicMock, patch
from decimal import Decimal
from CFOP.services.services import MotorFiscal
from CFOP.services.bases import FiscalContexto

class CFOPFlowIntegrationTest(SimpleTestCase):
    def setUp(self):
        self.banco = "saveweb001"

        self.cfop = MagicMock()
        self.cfop.cfop_codi = "5102"
        self.cfop.cfop_exig_icms = True
        self.cfop.cfop_exig_ipi = True
        self.cfop.cfop_exig_pis_cofins = False
        self.cfop.cfop_exig_cbs = False
        self.cfop.cfop_exig_ibs = False
        self.cfop.cfop_gera_st = False
        self.cfop.cfop_icms_base_inclui_ipi = True
        self.cfop.cfop_st_base_inclui_ipi = False
        self.cfop.fiscal = None

        self.ncm = MagicMock()
        self.ncm.ncmaliquota = MagicMock()
        self.ncm.fiscal = None

        self.produto = MagicMock()
        self.produto.prod_ncm = "12345678"
        fiscal_default = MagicMock()
        fiscal_default.cst_icms = None
        fiscal_default.aliq_icms = None
        fiscal_default.cst_ipi = None
        fiscal_default.aliq_ipi = None
        fiscal_default.cst_pis = None
        fiscal_default.aliq_pis = None
        fiscal_default.cst_cofins = None
        fiscal_default.aliq_cofins = None
        fiscal_default.cst_cbs = None
        fiscal_default.aliq_cbs = None
        fiscal_default.cst_ibs = None
        fiscal_default.aliq_ibs = None
        self.produto.fiscal = fiscal_default

    @patch("CFOP.auxiliares.aliquota_resolver.AliquotaResolver.resolver")
    def test_cfop_influences_tax_calculation(self, mock_resolver):
        # Setup Mock Aliquotas (IPI 10%)
        mock_resolver.return_value = {
            "ipi": Decimal("10.00"),
            "pis": Decimal("1.65"),
            "cofins": Decimal("7.60"),
            "cbs": None,
            "ibs": None
        }

        motor = MotorFiscal(banco=self.banco)

        # Context
        ctx = FiscalContexto(
            empresa_id=1,
            filial_id=1,
            banco=self.banco,
            regime="3", # Normal
            uf_origem="SP",
            uf_destino="RJ",
            produto=self.produto,
            cfop=self.cfop, # Explicitly passing our CFOP
            ncm=None
        )

        with patch.object(motor, "obter_icms_data", return_value={"icms": Decimal("12.00"), "mva_st": None, "st_aliq": None}), \
             patch.object(motor, "obter_ncm", return_value=None):
            # Calculate Item (Base = 100.00)
            base_manual = Decimal("100.00")
            resultado = motor.calcular_item(ctx, item=None, tipo_oper="VENDA", base_manual=base_manual)

        # Assertions
        
        # 1. IPI should be calculated because cfop_exig_ipi=True
        # Value = 100 * 10% = 10.00
        self.assertEqual(resultado["valores"]["ipi"], Decimal("10.00"))

        # 2. ICMS Base should include IPI because cfop_icms_base_inclui_ipi=True
        # Base ICMS = 100 + 10 = 110.00
        self.assertEqual(resultado["bases"]["icms"], Decimal("110.00"))

        # 3. ICMS Value (Interstate 12%)
        # 110 * 12% = 13.20
        self.assertEqual(resultado["valores"]["icms"], Decimal("13.20"))

        # 4. PIS/COFINS should be ZERO/None because cfop_exig_pis_cofins=False
        self.assertIsNone(resultado["valores"]["pis"])
        self.assertIsNone(resultado["valores"]["cofins"])

    @patch("CFOP.auxiliares.aliquota_resolver.AliquotaResolver.resolver")
    def test_cfop_disable_ipi(self, mock_resolver):
        self.cfop.cfop_exig_ipi = False

        mock_resolver.return_value = {
            "ipi": Decimal("10.00"),
            "pis": None, "cofins": None, "cbs": None, "ibs": None
        }

        motor = MotorFiscal(banco=self.banco)
        ctx = FiscalContexto(
            empresa_id=1,
            filial_id=1,
            banco=self.banco,
            regime="3",
            uf_origem="SP",
            uf_destino="RJ",
            produto=self.produto,
            cfop=self.cfop,
            ncm=None
        )

        with patch.object(motor, "obter_icms_data", return_value={"icms": Decimal("12.00"), "mva_st": None, "st_aliq": None}), \
             patch.object(motor, "obter_ncm", return_value=None):
            resultado = motor.calcular_item(ctx, item=None, tipo_oper="VENDA", base_manual=Decimal("100.00"))

        # IPI should be None
        self.assertIsNone(resultado["valores"]["ipi"])
        
        # ICMS Base should NOT include IPI (since IPI is 0/None)
        # Base ICMS = 100.00
        self.assertEqual(resultado["bases"]["icms"], Decimal("100.00"))
