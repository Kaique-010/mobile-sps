from types import SimpleNamespace

from django.conf import settings
from django.db import connections
from django.test import TestCase

from nfse.models import Nfse, NfseItem
from nfse.services.persistencia_service import PersistenciaNfseService
from core.licencas_loader import _bootstrap_licencas_web_if_missing, carregar_licencas_dict


class PersistenciaNfseServiceTest(TestCase):
    databases = '__all__'

    @classmethod
    def setUpTestData(cls):
        _bootstrap_licencas_web_if_missing()

        with connections['default'].cursor() as cur:
            cur.execute(
                """
                INSERT INTO licencas_web (slug, cnpj, db_name, db_host, db_port, modulos, db_user, db_password)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (slug) DO UPDATE SET
                    cnpj=EXCLUDED.cnpj,
                    db_name=EXCLUDED.db_name,
                    db_host=EXCLUDED.db_host,
                    db_port=EXCLUDED.db_port,
                    modulos=EXCLUDED.modulos,
                    db_user=EXCLUDED.db_user,
                    db_password=EXCLUDED.db_password
                """,
                (
                    'saveweb001',
                    '12345678000199',
                    'saveweb001',
                    'localhost',
                    '5432',
                    '[]',
                    'test',
                    'test',
                ),
            )
        connections['default'].commit()

        licencas = carregar_licencas_dict()
        licenca = next(
            (
                l for l in licencas
                if (l.get('db_name') or '').lower() == 'saveweb001'
                or (l.get('slug') or '').lower() == 'saveweb001'
            ),
            None,
        )
        cls.slug = (licenca or {}).get('slug') or 'saveweb001'
        cls.db_alias = cls.slug

        if cls.db_alias not in settings.DATABASES:
            default_cfg = dict(settings.DATABASES['default'])
            test_cfg = dict(default_cfg.get('TEST', {}) or {})
            test_cfg['MIRROR'] = 'default'
            alias_cfg = {**default_cfg, 'TEST': test_cfg}

            settings.DATABASES[cls.db_alias] = alias_cfg
            connections.databases[cls.db_alias] = alias_cfg
            connections.ensure_defaults(cls.db_alias)
            connections.prepare_test_settings(cls.db_alias)

    def setUp(self):
        self.context = SimpleNamespace(
            db_alias=self.db_alias,
            empresa_id=1,
            filial_id=1,
            slug=self.slug,
        )

    def _payload_base(self):
        return {
            'slug': self.slug,
            'municipio_codigo': '4119905',
            'rps_numero': '123',
            'rps_serie': '1',
            'prestador_documento': '12345678000199',
            'prestador_nome': 'SPS Tecnologia',
            'tomador_documento': '11111111111',
            'tomador_nome': 'Cliente Teste',
            'tomador_email': 'cliente@teste.com',
            'tomador_telefone': '42999999999',
            'tomador_endereco': 'Rua Teste',
            'tomador_numero': '100',
            'tomador_bairro': 'Centro',
            'tomador_cep': '84000000',
            'tomador_cidade': 'Ponta Grossa',
            'tomador_uf': 'PR',
            'servico_codigo': '1001',
            'servico_descricao': 'Servico teste',
            'cnae_codigo': '6201501',
            'lc116_codigo': '1.07',
            'natureza_operacao': '1',
            'valor_servico': '100.00',
            'valor_iss': '5.00',
            'valor_liquido': '95.00',
            'aliquota_iss': '5.0000',
            'iss_retido': False,
            'itens': [
                {
                    'descricao': 'Item 1',
                    'quantidade': '1.0000',
                    'valor_unitario': '100.000000',
                    'valor_total': '100.00',
                    'servico_codigo': '1001',
                    'cnae_codigo': '6201501',
                    'lc116_codigo': '1.07',
                }
            ]
        }

    def test_criar_rascunho_com_itens(self):
        nfse = PersistenciaNfseService.criar_rascunho(self.context, self._payload_base())

        self.assertIsInstance(nfse, Nfse)
        self.assertEqual(nfse.nfse_statu, 'rascunho')
        self.assertEqual(nfse.nfse_muni_codi, '4119905')

        itens = NfseItem.objects.using(self.db_alias).filter(nfsi_nfse_id=nfse.pk)
        self.assertEqual(itens.count(), 1)
        self.assertEqual(itens.first().nfsi_desc, 'Item 1')

    def test_salvar_envio(self):
        nfse = PersistenciaNfseService.criar_rascunho(self.context, self._payload_base())

        PersistenciaNfseService.salvar_envio(
            self.context,
            nfse,
            payload={'teste': 'ok'},
            xml_envio='<xml>envio</xml>',
            status='processando',
        )

        nfse.refresh_from_db()
        self.assertEqual(nfse.nfse_statu, 'processando')
        self.assertEqual(nfse.nfse_xml_envi, '<xml>envio</xml>')
        self.assertEqual(nfse.nfse_payl_envi, {'teste': 'ok'})

    def test_marcar_emitida(self):
        nfse = PersistenciaNfseService.criar_rascunho(self.context, self._payload_base())

        PersistenciaNfseService.marcar_emitida(self.context, nfse, {
            'numero': '999',
            'codigo_verificacao': 'ABC123',
            'protocolo': 'PROTO1',
            'xml_envio': '<xml>envio</xml>',
            'xml_retorno': '<xml>retorno</xml>',
        })

        nfse.refresh_from_db()
        self.assertEqual(nfse.nfse_statu, 'emitida')
        self.assertEqual(nfse.nfse_nume, '999')
        self.assertEqual(nfse.nfse_codi_veri, 'ABC123')

    def test_marcar_cancelada(self):
        nfse = PersistenciaNfseService.criar_rascunho(self.context, self._payload_base())

        PersistenciaNfseService.marcar_cancelada(self.context, nfse, {
            'status': 'cancelada',
            'xml_envio': '<xml>envio</xml>',
            'xml_retorno': '<xml>retorno</xml>',
        })

        nfse.refresh_from_db()
        self.assertEqual(nfse.nfse_statu, 'cancelada')
        self.assertIsNotNone(nfse.nfse_data_canc)

    def test_registrar_evento(self):
        nfse = PersistenciaNfseService.criar_rascunho(self.context, self._payload_base())

        evento = PersistenciaNfseService.registrar_evento(
            self.context,
            nfse_id=nfse.pk,
            tipo='emissao',
            payload={'ok': True},
            resposta={'numero': '1'},
            descricao='Evento teste',
        )

        self.assertEqual(evento.nfsev_tip, 'emissao')
        self.assertEqual(evento.nfsev_nfse_id, nfse.pk)
