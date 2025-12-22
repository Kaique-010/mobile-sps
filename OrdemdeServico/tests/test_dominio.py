from django.test import TestCase
from OrdemdeServico.dominio.ordem import Ordem
from OrdemdeServico.dominio.workflow import WorkflowOrdem
from OrdemdeServico.dominio.total import CalculadoraTotal
from OrdemdeServico.dominio.excecoes import ErroDominio

class TestOrdemDominio(TestCase):
    def test_criacao_ordem_sucesso(self):
        ordem = Ordem(prioridade=1)
        self.assertEqual(ordem.prioridade, 1)

    def test_criacao_ordem_prioridade_invalida(self):
        with self.assertRaises(ErroDominio):
            Ordem(prioridade=-1)

    def test_alterar_prioridade_sucesso(self):
        ordem = Ordem(prioridade=1)
        ordem.alterar_prioridade(2)
        self.assertEqual(ordem.prioridade, 2)

    def test_alterar_prioridade_invalida(self):
        ordem = Ordem(prioridade=1)
        with self.assertRaises(ErroDominio):
            ordem.alterar_prioridade(-1)

class TestWorkflowDominio(TestCase):
    def test_validar_avanco_sucesso(self):
        workflow = WorkflowOrdem(setor_atual=1)
        # Supondo que setor 2 é permitido
        workflow.validar_avanco(setor_destino=2, setores_permitidos=[2, 3])
        # Se não lançar exceção, passou

    def test_validar_avanco_invalido(self):
        workflow = WorkflowOrdem(setor_atual=1)
        with self.assertRaises(ErroDominio):
            workflow.validar_avanco(setor_destino=5, setores_permitidos=[2, 3])

class TestCalculadoraTotalDominio(TestCase):
    def test_calcular_total_sucesso(self):
        itens = [
            {"valor": 100},
            {"valor": 50.5},
            {"valor": 200}
        ]
        calc = CalculadoraTotal()
        total = calc.calcular(itens)
        self.assertEqual(total, 350.5)

    def test_calcular_total_vazio(self):
        itens = []
        calc = CalculadoraTotal()
        total = calc.calcular(itens)
        self.assertEqual(total, 0)

    def test_calcular_total_negativo(self):
        itens = [{"valor": -10}]
        calc = CalculadoraTotal()
        with self.assertRaises(ErroDominio):
            calc.calcular(itens)
