from decimal import Decimal

from django.test import TestCase

from core.utils import get_db_from_slug
from Produtos.models import Produtos, Ncm
from CFOP.models import CFOP, ProdutoFiscalPadrao, NcmFiscalPadrao, CFOPFiscalPadrao
from Notas_Fiscais.models import Nota, NotaItem, NotaItemImposto
from Notas_Fiscais.services.calculo_impostos_service import CalculoImpostosService
from Notas_Fiscais.dominio.builder import NotaBuilder


# Usamos o roteamento de licenças para apontar para um banco seguro (ex: 839/demonstracao)
TEST_DB_ALIAS = get_db_from_slug("demonstracao")


class HierarquiaIntegracaoNotaTests(TestCase):
    """
    Testa a hierarquia Produto -> CFOP -> NCM integrada:
    - MotorFiscal
    - CalculoImpostosService
    - Builder (DTO usado na geração do XML)
    """

    # Limitamos os testes a usarem apenas o alias configurado via licenças
    databases = {TEST_DB_ALIAS}

    def setUp(self):
        self.ncm = "71122000"

        self.cfop = CFOP.objects.using(TEST_DB_ALIAS).filter(
            cfop_empr=1,
            cfop_codi="5102",
        ).first()

        self.produto = Produtos.objects.using(TEST_DB_ALIAS).create(
            prod_empr=1,
            prod_codi="PROD001",
            prod_nome="PRODUTO TESTE",
            prod_ncm=self.ncm.ncm_codi,
        )

        self.nota = Nota.objects.using(TEST_DB_ALIAS).create(
            empresa=1,
            filial=1,
            modelo="55",
            serie="1",
            numero=1,
            tipo_operacao=1,
            finalidade=1,
            ambiente=2,
            destinatario_id=1,
        )

        self.item = NotaItem.objects.using(TEST_DB_ALIAS).create(
            nota=self.nota,
            produto=self.produto,
            quantidade=Decimal("1"),
            unitario=Decimal("100"),
            desconto=Decimal("0"),
            cfop=self.cfop.cfop_codi,
            ncm=self.ncm.ncm_codi,
        )

    def _rodar_calculo(self):
        CalculoImpostosService(TEST_DB_ALIAS).aplicar_impostos(self.nota)
        self.item = NotaItem.objects.using(TEST_DB_ALIAS).get(pk=self.item.pk)
        self.imposto = NotaItemImposto.objects.using(TEST_DB_ALIAS).get(item=self.item)

    def test_prioridade_produto_sobre_cfop_e_ncm(self):
        ProdutoFiscalPadrao.objects.create(
            produto=self.produto,
            aliq_icms=Decimal("18"),
        )
        CFOPFiscalPadrao.objects.create(
            cfop=self.cfop,
            aliq_icms=Decimal("12"),
        )
        NcmFiscalPadrao.objects.create(
            ncm=self.ncm,
            aliq_icms=Decimal("7"),
        )

        self._rodar_calculo()

        self.assertEqual(self.item.fonte_tributacao, "PRODUTO")
        self.assertEqual(self.imposto.icms_aliquota, Decimal("18"))

        dto = NotaBuilder(self.nota).build()
        dto_item = dto.itens[0]
        self.assertEqual(dto_item.aliq_icms, Decimal("18"))

    def test_prioridade_cfop_quando_nao_ha_produto(self):
        CFOPFiscalPadrao.objects.create(
            cfop=self.cfop,
            aliq_icms=Decimal("12"),
        )
        NcmFiscalPadrao.objects.create(
            ncm=self.ncm,
            aliq_icms=Decimal("7"),
        )

        self._rodar_calculo()

        self.assertEqual(self.item.fonte_tributacao, "CFOP")
        self.assertEqual(self.imposto.icms_aliquota, Decimal("12"))

    def test_prioridade_ncm_quando_apenas_ncm_tem_fiscal(self):
        NcmFiscalPadrao.objects.create(
            ncm=self.ncm,
            aliq_icms=Decimal("7"),
        )

        self._rodar_calculo()

        self.assertEqual(self.item.fonte_tributacao, "NCM")
        self.assertEqual(self.imposto.icms_aliquota, Decimal("7"))

