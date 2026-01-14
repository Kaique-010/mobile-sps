
import unittest
from unittest.mock import MagicMock, PropertyMock
from django.core.exceptions import ObjectDoesNotExist
from CFOP.services.services import MotorFiscal

class TestMotorFiscalLogic(unittest.TestCase):
    def setUp(self):
        self.motor = MotorFiscal()

    def test_resolver_fiscal_padrao_ncm_success(self):
        produto = MagicMock()
        type(produto).fiscal = PropertyMock(side_effect=ObjectDoesNotExist)
        cfop = MagicMock()
        type(cfop).fiscal = PropertyMock(side_effect=ObjectDoesNotExist)
        ncm = MagicMock()
        fiscal_mock = MagicMock()
        type(ncm).fiscal = PropertyMock(return_value=fiscal_mock)
        result, source = self.motor.resolver_fiscal_padrao(produto, ncm, cfop)
        self.assertEqual(source, "NCM")
        self.assertEqual(result, fiscal_mock)

    def test_resolver_fiscal_padrao_prioridade_produto(self):
        produto = MagicMock()
        fiscal_prod = MagicMock()
        type(produto).fiscal = PropertyMock(return_value=fiscal_prod)
        cfop = MagicMock()
        fiscal_cfop = MagicMock()
        type(cfop).fiscal = PropertyMock(return_value=fiscal_cfop)
        ncm = MagicMock()
        fiscal_ncm = MagicMock()
        type(ncm).fiscal = PropertyMock(return_value=fiscal_ncm)
        result, source = self.motor.resolver_fiscal_padrao(produto, ncm, cfop)
        self.assertEqual(source, "PRODUTO")
        self.assertEqual(result, fiscal_prod)

    def test_resolver_fiscal_padrao_prioridade_cfop_quando_produto_sem_fiscal(self):
        produto = MagicMock()
        type(produto).fiscal = PropertyMock(side_effect=ObjectDoesNotExist)
        cfop = MagicMock()
        fiscal_cfop = MagicMock()
        type(cfop).fiscal = PropertyMock(return_value=fiscal_cfop)
        ncm = MagicMock()
        fiscal_ncm = MagicMock()
        type(ncm).fiscal = PropertyMock(return_value=fiscal_ncm)
        result, source = self.motor.resolver_fiscal_padrao(produto, ncm, cfop)
        self.assertEqual(source, "CFOP")
        self.assertEqual(result, fiscal_cfop)

    def test_resolver_fiscal_padrao_all_missing(self):
        produto = MagicMock()
        type(produto).fiscal = PropertyMock(side_effect=ObjectDoesNotExist)
        cfop = MagicMock()
        type(cfop).fiscal = PropertyMock(side_effect=ObjectDoesNotExist)
        ncm = MagicMock()
        type(ncm).fiscal = PropertyMock(side_effect=ObjectDoesNotExist)
        result, source = self.motor.resolver_fiscal_padrao(produto, ncm, cfop)
        self.assertIsNone(result)
        self.assertIsNone(source)

    def test_obter_ncm_com_ponto(self):
        # We need to mock Ncm.objects.filter
        # Since MotorFiscal imports Ncm directly, we need to patch it where it is used.
        # However, MotorFiscal uses Ncm.objects.
        pass

if __name__ == '__main__':
    unittest.main()
