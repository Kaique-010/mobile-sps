from django.test import SimpleTestCase
from decimal import Decimal
from unittest.mock import MagicMock
from CFOP.services.auxiliares import ResolverAliquotaPorRegime
from CFOP.services.services import ResolverCST, FiscalContexto
from Notas_Fiscais.services.calculo_impostos_service import ResolverIncidencia

class TestResolvers(SimpleTestCase):
    def test_resolver_aliquota_simples(self):
        """Testa comportamento para Simples Nacional"""
        resolver = ResolverAliquotaPorRegime()
        
        # Mock NcmAliquota
        ncm_aliq = MagicMock()
        ncm_aliq.aliq_ipi = Decimal("10.00")
        # Definir explicitamente como None para evitar que MagicMock crie mocks filhos
        ncm_aliq.aliq_pis = None
        ncm_aliq.aliq_cofins = None
        ncm_aliq.aliq_cbs = None
        ncm_aliq.aliq_ibs = None
        
        # Regime Simples (1)
        res = resolver.resolver(ncm_aliq, "1")
        # Por enquanto retorna as alíquotas base, mas o logger registraria a decisão
        self.assertEqual(res["ipi"], Decimal("10.00"))

    def test_resolver_cst_simples(self):
        """Testa CST para Simples Nacional"""
        ctx = MagicMock(spec=FiscalContexto)
        ctx.regime = "1"
        ctx.fiscal_padrao = None
        
        cst_icms = ResolverCST.resolver_icms(ctx)
        self.assertEqual(cst_icms, "101") # Default CSOSN
        
        cst_pis = ResolverCST.resolver_pis_cofins(ctx)
        self.assertEqual(cst_pis, "49")

    def test_resolver_cst_normal(self):
        """Testa CST para Regime Normal"""
        ctx = MagicMock(spec=FiscalContexto)
        ctx.regime = "3"
        ctx.fiscal_padrao = None
        
        cst_icms = ResolverCST.resolver_icms(ctx)
        self.assertEqual(cst_icms, "00")
        
        cst_ipi = ResolverCST.resolver_ipi(ctx)
        self.assertEqual(cst_ipi, "50")

    def test_resolver_cst_override(self):
        """Testa Override de CST pelo cadastro"""
        ctx = MagicMock(spec=FiscalContexto)
        ctx.regime = "3"
        ctx.fiscal_padrao = MagicMock()
        ctx.fiscal_padrao.cst_icms = "60"
        
        cst_icms = ResolverCST.resolver_icms(ctx)
        self.assertEqual(cst_icms, "60")

    def test_resolver_incidencia_mock(self):
        """Testa se ResolverIncidencia processa o objeto CFOP"""
        cfop_mock = MagicMock()
        cfop_mock.cfop_exig_ipi = True
        
        nota_mock = MagicMock()
        
        res = ResolverIncidencia.aplicar_regras_nota(nota_mock, cfop_mock)
        self.assertTrue(res.cfop_exig_ipi)
