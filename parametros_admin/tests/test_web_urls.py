from django.test import SimpleTestCase
from django.urls import resolve, reverse


class ParametrosAdminWebURLsTest(SimpleTestCase):
    def test_list_url_resolves(self):
        url = reverse('parametros_admin_modulos', kwargs={'slug': 'casaa'})
        self.assertEqual(resolve(url).url_name, 'parametros_admin_modulos')

    def test_toggle_url_resolves(self):
        url = reverse('parametros_admin_toggle', kwargs={'slug': 'casaa', 'modulo_slug': 'Produtos'})
        self.assertEqual(resolve(url).url_name, 'parametros_admin_toggle')

