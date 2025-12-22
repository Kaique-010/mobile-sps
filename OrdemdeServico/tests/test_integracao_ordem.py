from django.test import TestCase
from OrdemdeServico.services import ordem_service
from OrdemdeServico.models import Ordemservico, Ordemservicopecas
from decimal import Decimal

class OrdemServiceIntegrationTest(TestCase):
    def setUp(self):
        self.user = None # Mock user or create one if needed
        self.banco = 'default'
        
    def test_criar_ordem_com_pecas(self):
        dados = {
            'orde_empr': 1,
            'orde_fili': 1,
            'orde_nume': 1000,
            'orde_tipo': '1',
            'orde_stat_orde': 0
        }
        
        pecas_data = [
            {
                'peca_codi': 'P001',
                'peca_quan': 2,
                'peca_unit': 50.00,
                'peca_tota': 100.00
            }
        ]
        
        servicos_data = []
        
        # Executa o serviço
        ordem = ordem_service.criar_ordem_servico(
            dados=dados,
            pecas_data=pecas_data,
            servicos_data=servicos_data,
            usuario=self.user,
            banco=self.banco
        )
        
        # Verificações
        self.assertTrue(Ordemservico.objects.filter(orde_nume=1000).exists())
        self.assertEqual(ordem.orde_tota, Decimal('100.00'))
        
        pecas = Ordemservicopecas.objects.filter(peca_orde=1000)
        self.assertEqual(pecas.count(), 1)
        self.assertEqual(pecas.first().peca_codi, 'P001')

    def test_atualizar_ordem_remover_peca(self):
        # Cria ordem inicial
        ordem = Ordemservico.objects.create(
            orde_empr=1, orde_fili=1, orde_nume=2000, orde_tota=100
        )
        Ordemservicopecas.objects.create(
            peca_empr=1, peca_fili=1, peca_orde=2000, peca_id=1,
            peca_codi='P1', peca_tota=100
        )
        
        # Atualiza removendo a peça (enviando lista vazia ou com outro item)
        # Se enviarmos lista vazia [], deve remover tudo? 
        # A lógica do repo é: remove o que NÃO está na lista de IDs enviados.
        # Se a lista é vazia, ids_enviados = [], remove tudo.
        
        pecas_data = [] # Lista vazia
        
        ordem_atualizada = ordem_service.atualizar_ordem_servico(
            ordem=ordem,
            dados={},
            pecas_data=pecas_data,
            servicos_data=[],
            usuario=self.user,
            banco=self.banco
        )
        
        self.assertEqual(Ordemservicopecas.objects.filter(peca_orde=2000).count(), 0)
        self.assertEqual(ordem_atualizada.orde_tota, 0)
