from django.test import TestCase, Client
from unittest.mock import patch


class TestHomeRouting(TestCase):
    def setUp(self):
        self.client = Client()

    @patch('Entidades.models.Entidades.objects')
    @patch('Pedidos.models.PedidoVenda.objects')
    @patch('Pedidos.models.Itenspedidovenda.objects')
    @patch('Pisos.models.Pedidospisos.objects')
    @patch('Pisos.models.Itenspedidospisos.objects')
    @patch('OrdemdeServico.models.Ordemservico.objects')
    def test_routes_os_by_slug(self, os_objs, itens_pisos, pisos, itens, pedidos, entidades):
        class FakeQS:
            def filter(self, *args, **kwargs):
                return self
            def order_by(self, *args, **kwargs):
                return self
            def aggregate(self, *args, **kwargs):
                return {'v': 0}
            def count(self):
                return 0
            def values_list(self, *args, **kwargs):
                return []
            def none(self):
                return self
            def using(self, *args, **kwargs):
                return self
        fake = FakeQS()
        entidades.using.return_value = fake
        pedidos.using.return_value = fake
        itens.using.return_value = fake
        pisos.using.return_value = fake
        itens_pisos.using.return_value = fake
        os_objs.using.return_value = fake

        s = self.client.session
        s['slug'] = 'eletrocometa'
        s.save()

        resp = self.client.get('/web/home/', {
            'data_inicio': '2025-01-01',
            'data_fim': '2025-01-31',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context.get('dashboard_variant'), 'os')

    @patch('Entidades.models.Entidades.objects')
    @patch('Pedidos.models.PedidoVenda.objects')
    @patch('Pedidos.models.Itenspedidovenda.objects')
    @patch('Pisos.models.Pedidospisos.objects')
    @patch('Pisos.models.Itenspedidospisos.objects')
    def test_routes_pisos_by_slug(self, itens_pisos, pisos, itens, pedidos, entidades):
        class FakeQS:
            def filter(self, *args, **kwargs):
                return self
            def order_by(self, *args, **kwargs):
                return self
            def aggregate(self, *args, **kwargs):
                return {'v': 0}
            def count(self):
                return 0
            def values_list(self, *args, **kwargs):
                return []
            def none(self):
                return self
            def using(self, *args, **kwargs):
                return self
        fake = FakeQS()
        entidades.using.return_value = fake
        pedidos.using.return_value = fake
        itens.using.return_value = fake
        pisos.using.return_value = fake
        itens_pisos.using.return_value = fake

        s = self.client.session
        s['slug'] = 'indusparquet'
        s.save()

        resp = self.client.get('/web/home/', {
            'data_inicio': '2025-01-01',
            'data_fim': '2025-01-31',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context.get('dashboard_variant'), 'pisos')
