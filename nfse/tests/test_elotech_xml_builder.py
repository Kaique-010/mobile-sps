from django.db import connections
from django.test import TestCase

from core.licencas_loader import _bootstrap_licencas_web_if_missing, carregar_licencas_dict
from nfse.builders.elotech_xml_builder import ElotechXmlBuilder


class ElotechXmlBuilderTest(TestCase):
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

    def setUp(self):
        self.builder = ElotechXmlBuilder()

    def _payload_base(self):
        return {
            'slug': self.slug,
            'prestador_documento': '12345678000199',
            'prestador_nome': 'SPS Tecnologia',
            'municipio_codigo': '4119905',
            'rps_numero': '123',
            'rps_serie': '1',
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
            'tomador_ie': '',
            'tomador_im': '',
            'servico_codigo': '1001',
            'servico_descricao': 'Serviço de desenvolvimento',
            'cnae_codigo': '6201501',
            'lc116_codigo': '1.07',
            'natureza_operacao': '1',
            'municipio_incidencia': '4119905',
            'municipio_servico': '4119905',
            'valor_servico': '100.00',
            'valor_deducao': '0.00',
            'valor_desconto': '0.00',
            'valor_inss': '0.00',
            'valor_irrf': '0.00',
            'valor_csll': '0.00',
            'valor_cofins': '0.00',
            'valor_pis': '0.00',
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

    def test_montar_xml_emissao(self):
        xml = self.builder.montar_xml_emissao(self._payload_base())

        self.assertIn('<emitirNfseRequest>', xml)
        self.assertIn('<prestadorDocumento>12345678000199</prestadorDocumento>', xml)
        self.assertIn('<servicoCodigo>1001</servicoCodigo>', xml)
        self.assertIn('<cnaeCodigo>6201501</cnaeCodigo>', xml)
        self.assertIn('<lc116Codigo>1.07</lc116Codigo>', xml)
        self.assertIn('<item>', xml)

    def test_montar_envelope_soap(self):
        xml_interno = '<teste>ok</teste>'
        envelope = self.builder.montar_envelope_soap(xml_interno)

        self.assertIn('<soapenv:Envelope', envelope)
        self.assertIn('<soapenv:Body>', envelope)
        self.assertIn('<teste>ok</teste>', envelope)

    def test_escape_xml(self):
        xml = self.builder.montar_xml_emissao({
            **self._payload_base(),
            'prestador_nome': 'SPS & Tecnologia <LTDA>',
        })

        self.assertIn('SPS &amp; Tecnologia &lt;LTDA&gt;', xml)

    def test_montar_xml_consulta(self):
        xml = self.builder.montar_xml_consulta({
            'numero': '10',
            'protocolo': 'ABC',
            'rps_numero': '123',
            'rps_serie': '1',
        })

        self.assertIn('<consultarNfseRequest>', xml)
        self.assertIn('<numero>10</numero>', xml)
        self.assertIn('<protocolo>ABC</protocolo>', xml)

    def test_montar_xml_cancelamento(self):
        xml = self.builder.montar_xml_cancelamento({
            'numero': '10',
            'codigo_verificacao': 'XYZ',
            'motivo': 'Erro de emissao',
        })

        self.assertIn('<cancelarNfseRequest>', xml)
        self.assertIn('<codigoVerificacao>XYZ</codigoVerificacao>', xml)
        self.assertIn('<motivo>Erro de emissao</motivo>', xml)
