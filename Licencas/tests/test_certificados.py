from django.test import TestCase, RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from Licencas.crypto import encrypt_str, decrypt_str, encrypt_bytes, decrypt_bytes
from Licencas.models import Filiais
from Licencas.serializers import FilialDetailSerializer
from Licencas.views import UploadCertificadoA1View

class CertificadosTests(TestCase):
    def test_crypto_str(self):
        s = 'senha123'
        enc = encrypt_str(s)
        dec = decrypt_str(enc)
        self.assertEqual(s, dec)

    def test_crypto_bytes(self):
        data = b'abc'
        enc = encrypt_bytes(data)
        dec = decrypt_bytes(enc)
        self.assertEqual(data, dec)

    def test_serializer_mascara(self):
        f = Filiais()
        f.empr_senh_cert = 'x'
        ser = FilialDetailSerializer(f)
        self.assertEqual(ser.data.get('senha_mascarada'), '********')

    def test_upload_invalido(self):
        rf = RequestFactory()
        view = UploadCertificadoA1View.as_view()
        file = SimpleUploadedFile('cert.p12', b'invalido', content_type='application/x-pkcs12')
        req = rf.post('/api/slug/licencas/filiais/upload-certificado/', {'empresa_id':1,'filial_id':1,'senha':'x'}, format='multipart')
        req.FILES['certificado'] = file
        resp = view(req, slug='slug')
        self.assertIn(resp.status_code, [400,404])
