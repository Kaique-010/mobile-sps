import logging

from Licencas.models import Filiais
from transportes.builders.mdfe_builder import MDFeBuilder
from transportes.models import Mdfe
from transportes.services.assinatura_service_mdfe import AssinaturaMDFeService

logger = logging.getLogger(__name__)


class MdfeEmissaoService:
    def __init__(self, mdfe: Mdfe, slug=None):
        self.mdfe = mdfe
        self.slug = slug

    def gerar_xml_assinado(self):
        db_alias = self.slug or self.mdfe._state.db or "default"
        filial = (
            Filiais.objects.using(db_alias)
            .defer("empr_cert_digi")
            .filter(empr_empr=self.mdfe.mdf_empr, empr_codi=self.mdfe.mdf_fili)
            .first()
        )
        if not filial:
            raise Exception("Filial não encontrada para emissão do MDFe.")

        builder = MDFeBuilder(self.mdfe, filial)
        xml = builder.build()
        chave = builder.chave

        assinador = AssinaturaMDFeService(self.mdfe)
        xml_assinado = assinador.assinar(xml)

        self.mdfe.mdf_xml_mdf = xml_assinado
        self.mdfe.mdf_chav = chave
        self.mdfe.save(using=db_alias)

        return {
            "chave": chave,
            "xml": xml_assinado,
        }
