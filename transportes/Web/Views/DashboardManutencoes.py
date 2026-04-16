from django.views.generic import TemplateView

from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.services.dashboard_manutencoes_service import (
    DashboardFiltros,
    DashboardManutencoesService,
)


class DashboardManutencoesView(TemplateView):
    template_name = "transportes/manutencoes_dashboard.html"

    def _get_banco(self):
        slug = self.kwargs.get("slug")
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id")

        service = DashboardManutencoesService()

        filtros = DashboardFiltros(
            frota=(self.request.GET.get("frota") or "").strip(),
            veiculo=(self.request.GET.get("veiculo") or "").strip(),
        )

        dados_movimentacao = service.buscar_movimentacoes(
            using=banco,
            empresa_id=empresa_id,
            filial_id=filial_id,
            filtros=filtros,
        )

        context.update(
            {
                "slug": self.kwargs.get("slug"),
                "titulo": "Dashboard de Manutenções",
                "filtros": filtros,
                "frotas": service.listar_frotas(
                    using=banco,
                    empresa_id=empresa_id,
                    filial_id=filial_id,
                ),
                "veiculos": service.listar_veiculos(
                    using=banco,
                    empresa_id=empresa_id,
                    frota=filtros.frota or None,
                ),
                **dados_movimentacao,
            }
        )

        return context
