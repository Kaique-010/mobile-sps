from django.test import TestCase
from django.core.cache import cache
from core.middleware import set_licenca_slug
from parametros_admin.models import Modulo, PermissaoModulo


class PermissoesCacheInvalidationTest(TestCase):
    def setUp(self):
        set_licenca_slug('default')

    def test_invalidate_cache_on_save(self):
        m = Modulo.objects.create(
            modu_nome='TesteModulo',
            modu_desc='Teste',
            modu_ativ=True,
            modu_icon='',
            modu_orde=1,
        )

        empresa_id = 1
        filial_id = 1
        key = f"modulos_licenca_default_{empresa_id}_{filial_id}"
        cache.set(key, ['stale'], 1800)

        p = PermissaoModulo(
            perm_empr=empresa_id,
            perm_fili=filial_id,
            perm_modu=m,
            perm_ativ=True,
            perm_usua_libe=0,
        )
        p.save(using='default')

        self.assertIsNone(cache.get(key))
