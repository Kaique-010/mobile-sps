from django.test import TestCase
from Agricola.models import LoteProdutos, ProdutoAgro, MovimentacaoEstoque, EstoqueFazenda
from Agricola.service.relatorios_service import RelatorioService
from decimal import Decimal
from django.utils import timezone

class RelatorioServiceTest(TestCase):
    def setUp(self):
        self.empresa = '1'
        self.filial = '1'
        
        # Criar Produto
        self.produto = ProdutoAgro.objects.create(
            prod_codi_agro='PROD01',
            prod_nome_agro='Milho',
            prod_cate_agro='Grãos',
            prod_unmd_agro='kg',
            prod_empr_agro=self.empresa,
            prod_fili_agro=self.filial,
            prod_cust_unit=Decimal('10.00')
        )
        
        self.produto2 = ProdutoAgro.objects.create(
            prod_codi_agro='PROD02',
            prod_nome_agro='Soja',
            prod_cate_agro='Grãos',
            prod_unmd_agro='kg',
            prod_empr_agro=self.empresa,
            prod_fili_agro=self.filial,
            prod_cust_unit=Decimal('20.00')
        )

        # Criar Lote para Milho
        self.lote = LoteProdutos.objects.create(
            lote_empr=self.empresa,
            lote_fili=self.filial,
            lote_ident='LOTE001',
            lote_prod=str(self.produto.id),
            lote_quant=Decimal('100.00'),
            lote_cust_unit=Decimal('10.00'),
            lote_data_venc=timezone.now().date()
        )
        
        # Criar Estoque para Soja (sem lote)
        EstoqueFazenda.objects.create(
            estq_faze='1',
            estq_prod=str(self.produto2.id),
            estq_quant=Decimal('50.00'),
            estq_cust_medi=Decimal('20.00'),
            estq_empr=self.empresa,
            estq_fili=self.filial
        )

        # Criar Movimentação
        MovimentacaoEstoque.objects.create(
            movi_estq_empr=self.empresa,
            movi_estq_fili=self.filial,
            movi_estq_faze='1',
            movi_estq_prod=str(self.produto.id),
            movi_estq_quant=Decimal('100.00'),
            movi_estq_tipo='entrada',
            movi_estq_cust_unit=Decimal('10.00')
        )

    def test_total_produtos_por_lote(self):
        resultado = RelatorioService.total_produtos_por_lote(self.empresa, self.filial)
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]['lote_ident'], 'LOTE001')
        self.assertEqual(resultado[0]['produto_nome'], 'Milho')
        self.assertEqual(resultado[0]['total_quantidade'], Decimal('100.00'))

    def test_total_produtos_sem_lote(self):
        resultado = RelatorioService.total_produtos_sem_lote(self.empresa, self.filial)
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]['produto_nome'], 'Soja')
        self.assertEqual(resultado[0]['estoque_total'], Decimal('50.00'))

    def test_extrato_movimentacao(self):
        resultado = RelatorioService.extrato_movimentacao(self.empresa, self.filial)
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]['produto_nome'], 'Milho')
        self.assertEqual(resultado[0]['tipo'], 'Entrada')
