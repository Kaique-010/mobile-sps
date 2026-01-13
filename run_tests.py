import os
import sys
import django
from django.conf import settings

# Add current directory to path
sys.path.append(os.getcwd())

class DisableMigrations:
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

if not settings.configured:
    settings.configure(
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'Licencas',
            'Entidades',
            'Produtos',
            'CFOP',
            'Notas_Fiscais',
        ],
        SECRET_KEY='secret',
        MIGRATION_MODULES=DisableMigrations()
    )
    django.setup()
    
    from django.core.management import call_command
    from django.apps import apps
    
    print("Forcing managed=True for all models...")
    for model in apps.get_models():
        model._meta.managed = True

    print("Running migrations (syncdb)...")
    call_command('migrate', verbosity=0, run_syncdb=True)
    print("Migrations completed.")

import unittest
# Use module strings to load tests
from CFOP.tests.test_resolvers import TestResolvers
from CFOP.tests.test_services import FiscalServiceTest
from CFOP.tests.test_emission_flow import EmissionFlowTest
from CFOP.tests.test_xml_generation import XmlGenerationTest
from CFOP.tests.test_sefaz_integration import TestSefazIntegration
from CFOP.tests.test_flow_integration import CFOPFlowIntegrationTest

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    # suite.addTests(loader.loadTestsFromTestCase(TestResolvers))
    # suite.addTests(loader.loadTestsFromTestCase(FiscalServiceTest))
    # suite.addTests(loader.loadTestsFromTestCase(EmissionFlowTest))
    # suite.addTests(loader.loadTestsFromTestCase(XmlGenerationTest))
    # suite.addTests(loader.loadTestsFromTestCase(TestSefazIntegration))
    suite.addTests(loader.loadTestsFromTestCase(CFOPFlowIntegrationTest))

    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
