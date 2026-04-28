from django.views.generic import TemplateView

from core.utils import get_db_from_slug
from processos.models import ChecklistItem, ChecklistModelo, ProcessoTipo
from processos.services.processo_service import ProcessoService


class ProcessoListView(TemplateView):
    template_name = "processos/processo_list.html"

    def _ctx(self):
        slug = self.kwargs.get("slug")
        return {
            "slug": slug,
            "db_alias": get_db_from_slug(slug) if slug else "default",
            "empresa": self.request.session.get("empresa_id", 1),
            "filial": self.request.session.get("filial_id", 1),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cfg = self._ctx()
        context.update(cfg)
        context["processos"] = ProcessoService.listar(
            db_alias=cfg["db_alias"],
            empresa=cfg["empresa"],
            filial=cfg["filial"],
        )
        context["tipos"] = ProcessoService.listar_tipos(
            db_alias=cfg["db_alias"],
            empresa=cfg["empresa"],
            filial=cfg["filial"],
        )
        context["modelos"] = ChecklistModelo.objects.using(cfg["db_alias"]).filter(
            chmo_empr=cfg["empresa"], chmo_fili=cfg["filial"]
        )
        context["itens"] = ChecklistItem.objects.using(cfg["db_alias"]).filter(
            chit_empr=cfg["empresa"], chit_fili=cfg["filial"]
        )
        context["nav_processos"] = [
            {"label": "Templates", "url": "processos:templates"},
            {"label": "Processos", "url": "processos:lista"},
        ]
        return context


class ProcessoTemplateNavView(TemplateView):
    template_name = "processos/templates_nav.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get("slug")
        db_alias = get_db_from_slug(slug) if slug else "default"
        empresa = self.request.session.get("empresa_id", 1)
        filial = self.request.session.get("filial_id", 1)
        context.update(
            {
                "slug": slug,
                "tipos": ProcessoTipo.objects.using(db_alias).filter(prot_empr=empresa, prot_fili=filial),
                "modelos": ChecklistModelo.objects.using(db_alias).filter(chmo_empr=empresa, chmo_fili=filial),
                "itens": ChecklistItem.objects.using(db_alias).filter(chit_empr=empresa, chit_fili=filial),
            }
        )
        return context
