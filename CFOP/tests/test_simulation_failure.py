
from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase
from ..services.services import MotorFiscal, FiscalContexto
from ..models import MapaCFOP, CFOP

class SimulationFailureTest(SimpleTestCase):
    def setUp(self):
        self.motor = MotorFiscal()
        self.ctx = FiscalContexto(
            empresa_id=1,
            filial_id=1,
            banco=None,
            regime="3",
            uf_origem="SP",
            uf_destino="SP",
            produto=MagicMock()
        )
        self.ctx.produto.prod_ncm = "36988552"
        self.ctx.produto.fiscal = None # Ensure no fiscal override by default

    @patch("CFOP.services.services.CFOP.objects")
    @patch("CFOP.services.services.MapaCFOP.objects")
    def test_simulation_fallback_when_mapa_missing(self, mock_mapa_objects, mock_cfop_objects):
        """
        Verifies that missing MapaCFOP triggers fallback to default CFOP (5102/6102).
        """
        # Simulate DoesNotExist on MapaCFOP
        mock_mapa_objects.select_related.return_value.get.side_effect = MapaCFOP.DoesNotExist
        
        # Mock Fallback CFOP (5102)
        mock_fallback_cfop = MagicMock()
        mock_fallback_cfop.cfop_codi = "5102"
        mock_fallback_cfop.cfop_exig_icms = True
        mock_fallback_cfop.cfop_exig_ipi = True
        mock_fallback_cfop.cfop_exig_pis_cofins = True
        mock_fallback_cfop.cfop_exig_cbs = False
        mock_fallback_cfop.cfop_exig_ibs = False
        mock_fallback_cfop.cfop_icms_base_inclui_ipi = False
        mock_fallback_cfop.cfop_gera_st = False
        mock_fallback_cfop.fiscal = None
        
        mock_cfop_objects.using.return_value.filter.return_value.first.return_value = mock_fallback_cfop
        mock_cfop_objects.filter.return_value.first.return_value = mock_fallback_cfop

        # Mock NCM with no fiscal override
        mock_ncm = MagicMock()
        mock_ncm.fiscal = None

        # Mock dependencies
        with patch.object(self.motor, 'obter_ncm', return_value=mock_ncm), \
             patch.object(self.motor, 'obter_icms_data', return_value={"icms": Decimal("18.00")}), \
             patch.object(self.motor, 'obter_aliquotas_base', return_value={"ipi": Decimal("10.00"), "pis": None, "cofins": None}), \
             patch.object(self.motor, 'aplicar_overrides_dif', side_effect=lambda n, c, a, i: (a, i)):
            
            result = self.motor.calcular_item(self.ctx, item=None, tipo_oper="VENDA", base_manual=Decimal("100.00"))
            
            # Verify fallback success
            self.assertIsNotNone(result["cfop"])
            self.assertEqual(result["cfop"].cfop_codi, "5102")
            self.assertEqual(result["valores"]["icms"], Decimal("18.00"))
            self.assertEqual(result["valores"]["ipi"], Decimal("10.00"))

    @patch("CFOP.services.services.MapaCFOP.objects")
    def test_simulation_succeeds_with_mapa_cfop(self, mock_mapa_objects):
        """
        Verifies that having a mapping results in calculated taxes.
        """
        # Simulate Finding a Mapping
        mock_mapa = MagicMock()
        mock_mapa.cfop.cfop_codi = "5102"
        mock_mapa.cfop.cfop_exig_icms = True
        mock_mapa.cfop.cfop_exig_ipi = True
        mock_mapa.cfop.cfop_exig_pis_cofins = True
        mock_mapa.cfop.cfop_exig_cbs = False
        mock_mapa.cfop.cfop_exig_ibs = False
        mock_mapa.cfop.cfop_icms_base_inclui_ipi = False
        mock_mapa.cfop.cfop_gera_st = False
        mock_mapa.cfop.fiscal = None
        
        # Mock success on the manager directly
        mock_mapa_objects.select_related.return_value.get.return_value = mock_mapa

        # Mock NCM with no fiscal override
        mock_ncm = MagicMock()
        mock_ncm.fiscal = None

        # Mock dependencies
        with patch.object(self.motor, 'obter_ncm', return_value=mock_ncm), \
             patch.object(self.motor, 'obter_icms_data', return_value={"icms": Decimal("18.00")}), \
             patch.object(self.motor, 'obter_aliquotas_base', return_value={"ipi": Decimal("10.00"), "pis": Decimal("1.65"), "cofins": Decimal("7.60")}), \
             patch.object(self.motor, 'aplicar_overrides_dif', side_effect=lambda n, c, a, i: (a, i)):
            
            result = self.motor.calcular_item(self.ctx, item=None, tipo_oper="VENDA", base_manual=Decimal("100.00"))
            
            # Verify success state
            self.assertIsNotNone(result["cfop"])
            self.assertEqual(result["cfop"].cfop_codi, "5102")
            self.assertEqual(result["valores"]["icms"], Decimal("18.00"))
            self.assertEqual(result["valores"]["ipi"], Decimal("10.00"))

    @patch("CFOP.services.services.MapaCFOP.objects")
    def test_ibs_cbs_override(self, mock_mapa_objects):
        """
        Verifies that IBS/CBS are calculated when overridden, even if CFOP doesn't require them.
        """
        # Simulate Finding a Mapping
        mock_mapa = MagicMock()
        mock_mapa.cfop.cfop_codi = "5102"
        mock_mapa.cfop.cfop_exig_icms = True
        mock_mapa.cfop.cfop_exig_cbs = False # Disabled in CFOP
        mock_mapa.cfop.cfop_exig_ibs = False # Disabled in CFOP
        mock_mapa.cfop.cfop_exig_ipi = False
        mock_mapa.cfop.cfop_exig_pis_cofins = False
        mock_mapa.cfop.cfop_icms_base_inclui_ipi = False
        mock_mapa.cfop.cfop_gera_st = False
        mock_mapa.cfop.fiscal = None
        
        mock_mapa_objects.select_related.return_value.get.return_value = mock_mapa

        # Override Fiscal with IBS/CBS
        fiscal_override = MagicMock()
        fiscal_override.aliq_cbs = Decimal("1.5")
        fiscal_override.aliq_ibs = Decimal("2.5")
        fiscal_override.cst_cbs = "02"
        fiscal_override.cst_ibs = "02"
        # Important: other fields might be accessed, set defaults
        fiscal_override.cst_icms = None
        fiscal_override.aliq_icms = None
        fiscal_override.cst_ipi = None
        fiscal_override.aliq_ipi = None
        fiscal_override.cst_pis = None
        fiscal_override.aliq_pis = None
        fiscal_override.cst_cofins = None
        fiscal_override.aliq_cofins = None
        
        self.ctx.produto.fiscal = fiscal_override

        # Mock dependencies
        with patch.object(self.motor, 'obter_ncm', return_value=None), \
             patch.object(self.motor, 'obter_icms_data', return_value={"icms": Decimal("18.00")}), \
             patch.object(self.motor, 'obter_aliquotas_base', return_value={}), \
             patch.object(self.motor, 'aplicar_overrides_dif', side_effect=lambda n, c, a, i: (a, i)):
            
            result = self.motor.calcular_item(self.ctx, item=None, tipo_oper="VENDA", base_manual=Decimal("100.00"))
            
            # Verify IBS/CBS calculated despite CFOP flag
            self.assertEqual(result["valores"]["cbs"], Decimal("1.50"))
            self.assertEqual(result["valores"]["ibs"], Decimal("2.50"))
