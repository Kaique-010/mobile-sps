from django.views.generic import FormView
from django.contrib import messages
from django.urls import reverse
from core.utils import get_licenca_db_config
from Produtos.models import Produtos
from coletaestoque.models import ColetaEstoque
from ..forms import ColetaLeituraForm


class ColetaRegistrarView(FormView):
    template_name = 'ColetaEstoque/coleta_registrar.html'
    form_class = ColetaLeituraForm

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.db_alias = get_licenca_db_config(request)
        self.empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or 1
        self.filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or 1
        self.usuario_id = getattr(request.user, 'usua_codi', None)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx

    def form_valid(self, form):
        dados = form.cleaned_data
        codigo_barras = dados['codigo_barras'].strip()
        quantidade = dados['quantidade']
        produto = Produtos.objects.using(self.db_alias).filter(prod_coba=codigo_barras).first()
        if not produto:
            messages.error(self.request, 'Produto não encontrado pelo código de barras informado.')
            return self.form_invalid(form)
        try:
            uid = None
            try:
                uid = int(self.usuario_id) if self.usuario_id is not None else None
            except Exception:
                uid = None
            if uid is None:
                try:
                    uid = int(self.request.session.get('usuario_id'))
                except Exception:
                    uid = None
            ColetaEstoque.objects.using(self.db_alias).create(
                cole_prod=produto.prod_codi,
                cole_quan_lida=quantidade,
                cole_usua_id=uid or 1,
                cole_empr=int(self.empresa_id) if self.empresa_id else 1,
                cole_fili=int(self.filial_id) if self.filial_id else 1,
            )
            messages.success(self.request, 'Leitura registrada com sucesso.')
        except Exception as e:
            messages.error(self.request, f'Falha ao registrar leitura: {e}')
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return f"/web/{self.slug}/coleta-estoque/resumo/"
