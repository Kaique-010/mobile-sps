from datetime import date

from core.utils import get_db_from_slug
from transportes.models import Mdfe


class MdfeEncerramentoService:
    """Serviço de encerramento de MDF-e seguindo padrão multi-db por slug."""

    def __init__(self, mdfe: Mdfe, slug: str | None = None):
        self.mdfe = mdfe
        self.slug = slug

    def encerrar(self, uf: str | None = None, cmun: str | None = None):
        db_alias = self._resolve_db_alias()

        uf_encerramento = (uf or self.mdfe.mdf_esta_dest or "").strip()
        cmun_encerramento = cmun or self.mdfe.mdf_cida_carr

        self.mdfe.mdf_fina = True
        self.mdfe.mdf_data_ence = date.today()
        self.mdfe.mdf_esta_ence = uf_encerramento or self.mdfe.mdf_esta_ence
        self.mdfe.mdf_cida_ence = cmun_encerramento or self.mdfe.mdf_cida_ence
        self.mdfe.save(using=db_alias)

        return {
            "ok": True,
            "mdf_id": self.mdfe.mdf_id,
            "mdf_fina": self.mdfe.mdf_fina,
            "mdf_data_ence": self.mdfe.mdf_data_ence,
            "mdf_esta_ence": self.mdfe.mdf_esta_ence,
            "mdf_cida_ence": self.mdfe.mdf_cida_ence,
        }

    def _resolve_db_alias(self):
        if self.slug:
            return get_db_from_slug(self.slug)
        return self.mdfe._state.db or "default"
