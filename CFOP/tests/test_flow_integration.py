from django.test import TestCase
from unittest.mock import MagicMock, patch
from decimal import Decimal
from CFOP.models import CFOP, MapaCFOP, TabelaICMS
from CFOP.services.services import MotorFiscal
from CFOP.services.bases import FiscalContexto
from Produtos.models import Produtos, Ncm, UnidadeMedida, NcmAliquota

class CFOPFlowIntegrationTest(TestCase):
    databases = {'default'}

    def setUp(self):
        # 1. Create CFOP with specific flags
        self.cfop = CFOP.objects.create(
            cfop_empr=1,
            cfop_codi="5102",
            cfop_desc="Venda de Mercadoria",
            cfop_exig_icms=True,
            cfop_exig_ipi=True, # Let's test IPI
            cfop_exig_pis_cofins=False,
            cfop_exig_cbs=False,
            cfop_exig_ibs=False,
            cfop_gera_st=False,
            cfop_icms_base_inclui_ipi=True # Test base calculation
        )

        # 2. Create NCM and Product
        self.ncm = Ncm.objects.create(ncm_codi="12345678", ncm_desc="Teste")
        
        # Create NcmAliquota (required by MotorFiscal)
        NcmAliquota.objects.create(
            nali_ncm=self.ncm,
            nali_empr=1,
            nali_aliq_ipi=Decimal("10.00"),
            nali_aliq_pis=Decimal("1.65"),
            nali_aliq_cofins=Decimal("7.60"),
            nali_aliq_cbs=Decimal("0.00"),
            nali_aliq_ibs=Decimal("0.00")
        )
        
        self.unidade = UnidadeMedida.objects.create(
            unid_codi="UN",
            unid_desc="UNIDADE"
        )
        
        self.produto = Produtos.objects.create(
            prod_codi="PROD01",
            prod_nome="Produto Teste",
            prod_ncm="12345678",
            prod_unme=self.unidade
        )

        # 3. Setup ICMS Table
        TabelaICMS.objects.create(
            empresa=1,
            uf_origem="SP",
            uf_destino="RJ",
            aliq_interna=Decimal("18.00"),
            aliq_inter=Decimal("12.00"),
            mva_st=Decimal("50.00")
        )

    @patch("CFOP.services.services.ResolverAliquotaPorRegime.resolver")
    def test_cfop_influences_tax_calculation(self, mock_resolver):
        # Setup Mock Aliquotas (IPI 10%)
        mock_resolver.return_value = {
            "ipi": Decimal("10.00"),
            "pis": Decimal("1.65"),
            "cofins": Decimal("7.60"),
            "cbs": None,
            "ibs": None
        }

        # Initialize MotorFiscal
        motor = MotorFiscal(banco="default")

        # Context
        ctx = FiscalContexto(
            empresa_id=1,
            filial_id=1,
            banco="default",
            regime="3", # Normal
            uf_origem="SP",
            uf_destino="RJ",
            produto=self.produto,
            cfop=self.cfop, # Explicitly passing our CFOP
            ncm=self.ncm
        )

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

    @patch("CFOP.services.services.ResolverAliquotaPorRegime.resolver")
    def test_cfop_disable_ipi(self, mock_resolver):
        # Update CFOP to disable IPI
        self.cfop.cfop_exig_ipi = False
        self.cfop.save()

        mock_resolver.return_value = {
            "ipi": Decimal("10.00"),
            "pis": None, "cofins": None, "cbs": None, "ibs": None
        }

        motor = MotorFiscal(banco="default")
        ctx = FiscalContexto(
            empresa_id=1,
            filial_id=1,
            banco="default",
            regime="3",
            uf_origem="SP",
            uf_destino="RJ",
            produto=self.produto,
            cfop=self.cfop,
            ncm=self.ncm
        )

        resultado = motor.calcular_item(ctx, item=None, tipo_oper="VENDA", base_manual=Decimal("100.00"))

        # IPI should be None
        self.assertIsNone(resultado["valores"]["ipi"])
        
        # ICMS Base should NOT include IPI (since IPI is 0/None)
        # Base ICMS = 100.00
        self.assertEqual(resultado["bases"]["icms"], Decimal("100.00"))

