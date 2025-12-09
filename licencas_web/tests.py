from django.test import TransactionTestCase
from licencas_web.models import LicencaWeb
from core.utils import get_db_from_slug, get_licenca_db_config
from django.conf import settings
from django.db import connections
import os


class LicencasRoutingTests(TransactionTestCase):

    def setUp(self):
        LicencaWeb.objects.update_or_create(
            slug='save1',
            defaults={
                'cnpj': '13446907000120',
                'db_name': 'savexml1',
                'db_host': 'base.rtalmeida.com.br',
                'db_port': '5432',
                'modulos': '[]',
                'db_user': 'user_save1',
                'db_password': 'pass_save1',
            }
        )

    def test_get_db_from_slug_uses_db_credentials(self):
        alias = get_db_from_slug('save1')
        self.assertEqual(alias, 'save1')
        conf = settings.DATABASES['save1']
        self.assertEqual(conf['USER'], 'user_save1')
        self.assertEqual(conf['PASSWORD'], 'pass_save1')
        self.assertEqual(conf['NAME'], 'savexml1')
        self.assertEqual(conf['HOST'], 'base.rtalmeida.com.br')
        self.assertEqual(conf['PORT'], '5432')

    def test_fallback_to_env_when_no_db_credentials(self):
        os.environ['IPA_DB_USER'] = 'user_ipa'
        os.environ['IPA_DB_PASSWORD'] = 'pass_ipa'
        alias = get_db_from_slug('ipa')
        self.assertEqual(alias, 'ipa')
        conf = settings.DATABASES['ipa']
        self.assertEqual(conf['USER'], 'user_ipa')
        self.assertEqual(conf['PASSWORD'], 'pass_ipa')

    def test_get_licenca_db_config_from_request_path(self):
        class R:
            path = '/api/save1/entidades/'
            headers = {}
            session = {}

        db_alias = get_licenca_db_config(R())
        self.assertIn(db_alias, ['save1', 'default'])
