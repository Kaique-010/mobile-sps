from django.test import TestCase
from parametros_admin.models import Modulo

class ModuloSyncTests(TestCase):
    def test_sync_installed_apps_creates_records(self):
        result = Modulo.sync_installed_apps()
        self.assertGreaterEqual(result['total'], 1)
        self.assertTrue(
            Modulo.objects.filter(modu_nome='parametros_admin').exists()
        )
