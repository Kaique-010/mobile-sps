from django.test import TestCase
from django.contrib.contenttypes.models import ContentType

from perfilweb.services import _buscar_contenttype, normalizar_app_label


class TestPerfilDashboardAliases(TestCase):
    def test_normalizar_app_label_dashboard_aliases(self):
        self.assertEqual(normalizar_app_label('dashboards'), 'dash')
        self.assertEqual(normalizar_app_label('dashboard'), 'dash')
        self.assertEqual(normalizar_app_label('dash-board'), 'dash')
        self.assertEqual(normalizar_app_label('DashBoards'), 'dash')

    def test_buscar_contenttype_aceita_aliases_de_dashboard(self):
        ContentType.objects.create(app_label='dashboard', model='vendas')
        ct, estrategia = _buscar_contenttype('default', 'dash', 'vendas')
        self.assertIsNotNone(ct)
        self.assertEqual(ct.app_label, 'dashboard')
        self.assertIn('busca_direta', estrategia)
