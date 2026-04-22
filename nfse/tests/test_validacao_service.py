from django.core.exceptions import ValidationError
from django.db import connections
from django.test import TestCase

from core.licencas_loader import _bootstrap_licencas_web_if_missing, carregar_licencas_dict
from nfse.services.validacao_service import ValidacaoNfseService


class ValidacaoNfseServiceTest(TestCase):
    databases = {'default'}

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

    def _payload_base(self):
        return {
            'slug': self.slug,
            'municipio_codigo': '4119905',
            'rps_numero': '123',
            'prestador_documento': '12345678000199',
            'prestador_nome': 'SPS Tecnologia',
            'tomador_documento': '11111111111',
            'tomador_nome': 'Cliente Teste',
            'servico_codigo': '1001',
            'servico_descricao': 'Serviço de desenvolvimento',
            'cnae_codigo': '6201501',
            'lc116_codigo': '1.07',
            'valor_servico': '100.00',
            'valor_iss': '5.00',
            'valor_liquido': '95.00',
            'aliquota_iss': '5.0000',
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

    def test_validar_payload_ok(self):
        data = self._payload_base()
        ValidacaoNfseService.validar_payload(data)

    def test_deve_erro_sem_campos_obrigatorios(self):
        data = {}
        with self.assertRaises(ValidationError) as exc:
            ValidacaoNfseService.validar_payload(data)

        self.assertIn('municipio_codigo', exc.exception.message_dict)
        self.assertIn('rps_numero', exc.exception.message_dict)

    def test_deve_erro_valor_servico_zerado(self):
        data = self._payload_base()
        data['valor_servico'] = '0.00'

        with self.assertRaises(ValidationError) as exc:
            ValidacaoNfseService.validar_payload(data)

        self.assertIn('valor_servico', exc.exception.message_dict)

    def test_deve_erro_sem_cnae_em_ponta_grossa(self):
        data = self._payload_base()
        data['cnae_codigo'] = ''

        with self.assertRaises(ValidationError) as exc:
            ValidacaoNfseService.validar_payload(data)

        self.assertIn('cnae_codigo', exc.exception.message_dict)

    def test_deve_erro_sem_lc116_em_ponta_grossa(self):
        data = self._payload_base()
        data['lc116_codigo'] = ''

        with self.assertRaises(ValidationError) as exc:
            ValidacaoNfseService.validar_payload(data)

        self.assertIn('lc116_codigo', exc.exception.message_dict)

    def test_deve_erro_quando_soma_itens_diferente_valor_servico(self):
        data = self._payload_base()
        data['itens'][0]['valor_total'] = '50.00'

        with self.assertRaises(ValidationError) as exc:
            ValidacaoNfseService.validar_payload(data)

        self.assertIn('valor_servico', exc.exception.message_dict)

    def test_deve_erro_item_sem_descricao(self):
        data = self._payload_base()
        data['itens'][0]['descricao'] = ''

        with self.assertRaises(ValidationError) as exc:
            ValidacaoNfseService.validar_payload(data)

        self.assertIn('itens', exc.exception.message_dict)
