from django.test import TestCase
from decimal import Decimal
from Produtos.models import Produtos, Ncm
from CFOP.models import CFOP, ProdutoFiscalPadrao, NcmFiscalPadrao, CFOPFiscalPadrao
from CFOP.services.services import MotorFiscal

class HierarquiaFiscalTests(TestCase):
    def setUp(self):
        self.motor = MotorFiscal()
        
        # Create common objects
        # Note: Adjust fields as per actual model definitions if defaults are missing
        self.ncm = Ncm.objects.create(ncm_codigo="12345678", ncm_desc="Teste NCM")
        self.cfop = CFOP.objects.create(cfop_codi="5102", cfop_desc="Venda", cfop_empr=1)
        self.produto = Produtos.objects.create(
            prod_codi="TESTE", prod_desc="Produto Teste", 
            prod_ncm=self.ncm.ncm_codigo, prod_empr=1
        )
        
    def test_prioridade_produto(self):
        # Setup: All 3 have fiscal
        ProdutoFiscalPadrao.objects.create(produto=self.produto, aliq_icms=Decimal("18"))
        CFOPFiscalPadrao.objects.create(cfop=self.cfop, aliq_icms=Decimal("12"))
        NcmFiscalPadrao.objects.create(ncm=self.ncm, aliq_icms=Decimal("7"))
        
        fiscal, source = self.motor.resolver_fiscal_padrao(self.produto, self.ncm, self.cfop)
        
        self.assertEqual(source, "PRODUTO")
        self.assertEqual(fiscal.aliq_icms, Decimal("18"))

    def test_prioridade_cfop(self):
        # Setup: CFOP and NCM have fiscal, Product does not
        CFOPFiscalPadrao.objects.create(cfop=self.cfop, aliq_icms=Decimal("12"))
        NcmFiscalPadrao.objects.create(ncm=self.ncm, aliq_icms=Decimal("7"))
        
        fiscal, source = self.motor.resolver_fiscal_padrao(self.produto, self.ncm, self.cfop)
        
        self.assertEqual(source, "CFOP")
        self.assertEqual(fiscal.aliq_icms, Decimal("12"))

    def test_prioridade_ncm(self):
        # Setup: Only NCM has fiscal
        NcmFiscalPadrao.objects.create(ncm=self.ncm, aliq_icms=Decimal("7"))
        
        fiscal, source = self.motor.resolver_fiscal_padrao(self.produto, self.ncm, self.cfop)
        
        self.assertEqual(source, "NCM")
        self.assertEqual(fiscal.aliq_icms, Decimal("7"))
        
    def test_sem_fiscal(self):
        fiscal, source = self.motor.resolver_fiscal_padrao(self.produto, self.ncm, self.cfop)
        self.assertIsNone(fiscal)
        self.assertIsNone(source)
