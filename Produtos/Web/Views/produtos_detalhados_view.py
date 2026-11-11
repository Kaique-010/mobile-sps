# Produtos/Web/Views/produtos_detalhados_view.py
"""Relatório de Produtos Detalhados (view produtos_detalhados) com paginação
no padrão da aplicação (50 itens por página) e infinite scroll.
"""

from urllib.parse import quote_plus

from django.http import HttpResponse
from django.views import View
from django.views.generic import ListView

from Produtos.models import ProdutosDetalhados
from Produtos.servicos.produtos_detalhados_service import ProdutosDetalhadosService

from .web_views import DBAndSlugMixin

FILTROS_RELATORIO = (
    "codigo",
    "nome",
    "grupo",
    "marca",
    "ncm",
    "codigo_do_fabricante",
    "estoque",
    "ordenar",
)


def _ler_filtros(request):
    return {campo: (request.GET.get(campo) or "").strip() for campo in FILTROS_RELATORIO}


class ProdutosDetalhadosListView(DBAndSlugMixin, ListView):
    model = ProdutosDetalhados
    template_name = "Produtos/produtos_detalhados_list.html"
    context_object_name = "produtos"
    paginate_by = ProdutosDetalhadosService.PAGE_SIZE

    def _filtros(self):
        return _ler_filtros(self.request)

    def get_queryset(self):
        self.service = ProdutosDetalhadosService(
            db_alias=self.db_alias,
            empresa=self.empresa_id,
            filial=self.filial_id,
        )
        return self.service.get_queryset(filtros=self._filtros())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.slug
        ctx["filters"] = self._filtros()
        ctx["extra_query"] = "".join(
            f"&{campo}={quote_plus(valor)}"
            for campo, valor in ctx["filters"].items()
            if valor
        )
        return ctx


class ExportarProdutosDetalhadosView(DBAndSlugMixin, View):
    """Exporta o relatório de Produtos Detalhados para Excel (xlsx)."""

    def get(self, request, *args, **kwargs):
        service = ProdutosDetalhadosService(
            db_alias=self.db_alias,
            empresa=self.empresa_id,
            filial=self.filial_id,
        )
        wb = service.gerar_excel(filtros=_ler_filtros(request))

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="produtos_detalhados.xlsx"'
        wb.save(response)
        return response


class ImprimirProdutosDetalhadosView(DBAndSlugMixin, View):
    """Imprime o relatório de Produtos Detalhados em PDF (paisagem)."""

    def get(self, request, *args, **kwargs):
        service = ProdutosDetalhadosService(
            db_alias=self.db_alias,
            empresa=self.empresa_id,
            filial=self.filial_id,
        )
        usuario = None
        if request.user.is_authenticated:
            usuario = request.user.get_username() or request.user.username

        buffer = service.gerar_pdf(filtros=_ler_filtros(request), usuario=usuario)

        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="produtos_detalhados.pdf"'
        return response
