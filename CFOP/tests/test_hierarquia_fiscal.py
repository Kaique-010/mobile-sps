from django.test import SimpleTestCase
from decimal import Decimal
from unittest.mock import MagicMock

from CFOP.auxiliares.fiscal_padrao_resolver import FiscalPadraoResolver
from CFOP.models import CFOPFiscalPadrao, NcmFiscalPadrao, ProdutoFiscalPadrao

class HierarquiaFiscalTests(SimpleTestCase):
    def setUp(self):
        self.resolver = FiscalPadraoResolver()

        self.produto = MagicMock()
        self.produto.pk = 1
        self.produto.fiscal = None

        self.cfop = MagicMock()
        self.cfop.pk = 2
        self.cfop.fiscal = None

        self.ncm = MagicMock()
        self.ncm.pk = 3
        self.ncm.fiscal = None

        class FakeQS:
            def __init__(self, result):
                self._result = result

            def using(self, _):
                return self

            def filter(self, **_):
                return self

            def first(self):
                return self._result

        self.FakeQS = FakeQS
        
    def test_prioridade_produto(self):
        fiscal_prod = MagicMock()
        fiscal_prod.aliq_icms = Decimal("18")

        fiscal_cfop = MagicMock()
        fiscal_cfop.aliq_icms = Decimal("12")

        fiscal_ncm = MagicMock()
        fiscal_ncm.aliq_icms = Decimal("7")

        mapping = {
            ProdutoFiscalPadrao: fiscal_prod,
            CFOPFiscalPadrao: fiscal_cfop,
            NcmFiscalPadrao: fiscal_ncm,
        }

        self.resolver._qs = lambda model: self.FakeQS(mapping.get(model))
        fiscal, source = self.resolver.resolver(self.produto, self.ncm, self.cfop)
        
        self.assertEqual(source, "PRODUTO")
        self.assertEqual(fiscal.aliq_icms, Decimal("18"))

    def test_prioridade_cfop(self):
        fiscal_cfop = MagicMock()
        fiscal_cfop.aliq_icms = Decimal("12")

        fiscal_ncm = MagicMock()
        fiscal_ncm.aliq_icms = Decimal("7")

        mapping = {
            ProdutoFiscalPadrao: None,
            CFOPFiscalPadrao: fiscal_cfop,
            NcmFiscalPadrao: fiscal_ncm,
        }

        self.resolver._qs = lambda model: self.FakeQS(mapping.get(model))
        fiscal, source = self.resolver.resolver(self.produto, self.ncm, self.cfop)
        
        self.assertEqual(source, "CFOP")
        self.assertEqual(fiscal.aliq_icms, Decimal("12"))

    def test_prioridade_ncm(self):
        fiscal_ncm = MagicMock()
        fiscal_ncm.aliq_icms = Decimal("7")

        mapping = {
            ProdutoFiscalPadrao: None,
            CFOPFiscalPadrao: None,
            NcmFiscalPadrao: fiscal_ncm,
        }

        self.resolver._qs = lambda model: self.FakeQS(mapping.get(model))
        fiscal, source = self.resolver.resolver(self.produto, self.ncm, self.cfop)
        
        self.assertEqual(source, "NCM")
        self.assertEqual(fiscal.aliq_icms, Decimal("7"))
        
    def test_sem_fiscal(self):
        mapping = {
            ProdutoFiscalPadrao: None,
            CFOPFiscalPadrao: None,
            NcmFiscalPadrao: None,
        }

        self.resolver._qs = lambda model: self.FakeQS(mapping.get(model))
        fiscal, source = self.resolver.resolver(self.produto, self.ncm, self.cfop)
        self.assertIsNone(fiscal)
        self.assertIsNone(source)

    def test_prioriza_relacionamento_fiscal_direto(self):
        fiscal_prod = MagicMock()
        fiscal_prod.aliq_icms = Decimal("18")
        self.produto.fiscal = fiscal_prod

        spy = MagicMock()
        self.resolver._qs = spy

        fiscal, source = self.resolver.resolver(self.produto, self.ncm, self.cfop)

        self.assertEqual(source, "PRODUTO")
        self.assertEqual(fiscal.aliq_icms, Decimal("18"))
        spy.assert_not_called()
