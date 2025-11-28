from django.db import transaction

from ..models import Nota, NotaItemImposto
from ..dominio.builder import NotaBuilder
from ..infrastructure.certificado_loader import CertificadoLoader
from ..infrastructure.sefaz_adapter import SefazAdapter
from ..services.calculo_impostos_service import CalculoImpostosService
from .construir_nfe_pynfe import construir_nfe_pynfe

class EmissaoService:

    def __init__(self, slug, database):
        self.slug = slug
        self.db = database

    def emitir(self, nota_id):
        nota = Nota.objects.using(self.db).get(id=nota_id)

        # 1) Calcular impostos item a item
        CalculoImpostosService(self.db).aplicar_impostos(nota)

        # 2) Montar DTO
        dto = NotaBuilder(nota, database=self.db).build()

        # 3) Montar objeto NFe (PyNFe)
        nfe_obj = construir_nfe_pynfe(dto)

        # 4) Certificado
        from Licencas.models import Filiais
        filial_obj = Filiais.objects.using(self.db).get(empr_empr=nota.empresa, empr_codi=nota.filial)
        cert_path, cert_pass = CertificadoLoader(filial_obj).load()

        # 5) Conexão SEFAZ
        adapter = SefazAdapter(cert_path, cert_pass, dto.emitente.uf, dto.ambiente)

        # 6) Emitir
        resposta = adapter.emitir(nfe_obj)

        # 7) Persistir
        with transaction.atomic(using=self.db):
            nota.chave_acesso = resposta.get("chave")
            nota.protocolo_autorizacao = resposta.get("protocolo")
            nota.xml_assinado = resposta["xml"]
            nota.status = resposta.get("status", 0)
            nota.save(using=self.db)

        return resposta
