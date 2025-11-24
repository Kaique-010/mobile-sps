from django.test import SimpleTestCase
from django.urls import resolve
from contas_a_pagar.Web.listar import TitulosPagarListView


class WebRoutingContasAPagarTest(SimpleTestCase):
    def test_resolve_list_view(self):
        match = resolve('/web/x/contas-a-pagar/')
        self.assertEqual(match.func.view_class, TitulosPagarListView)