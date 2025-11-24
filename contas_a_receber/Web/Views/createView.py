from django.views.generic import CreateView
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ..mixin import DBAndSlugMixin
from ..forms import TitulosReceberForm
from ...models import Titulosreceber


class TitulosReceberCreateView(DBAndSlugMixin, CreateView):
    model = Titulosreceber
    form_class = TitulosReceberForm
    template_name = 'ContasAReceber/titulo_receber_criar.html'
    
    def cliente_nome(self, cliente_id):
        banco = get_licenca_db_config(self.request) or 'default'
        from Entidades.models import Entidades
        try:
            cli = int(cliente_id)
        except (TypeError, ValueError):
            return ''
        try:
            emp = int(self.empresa_id) if self.empresa_id is not None else None
        except (TypeError, ValueError):
            emp = self.empresa_id
        qs = Entidades.objects.using(banco)
        qs = qs.filter(enti_clie=cli)
        if emp is not None:
            qs = qs.filter(enti_empr=emp)
        row = qs.values('enti_nome').first()
        return row.get('enti_nome') if row else ''
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.get('form')
        cliente_id = None
        if form:
            cliente_id = (form.data.get('titu_clie') or form.initial.get('titu_clie'))
        context['cliente_nome'] = (self.cliente_nome(cliente_id) if cliente_id else '') 
        return context

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        dados = form.cleaned_data
        emp = (self.request.session.get('empresa_id')
               or self.request.headers.get('X-Empresa')
               or self.request.GET.get('titu_empr')
               or getattr(self, 'empresa_id', None))
        fil = (self.request.session.get('filial_id')
               or self.request.headers.get('X-Filial')
               or self.request.GET.get('titu_fili')
               or getattr(self, 'filial_id', None))
        if emp is not None:
            try:
                dados['titu_empr'] = int(emp)
            except Exception:
                dados['titu_empr'] = emp
        if fil is not None:
            try:
                dados['titu_fili'] = int(fil)
            except Exception:
                dados['titu_fili'] = fil
        from ...services import criar_titulo_receber
        criar_titulo_receber(
            banco=banco,
            dados=dados,
            empresa_id=(dados.get('titu_empr') or emp),
            filial_id=(dados.get('titu_fili') or fil)
        )
        return redirect('contas_a_receber_web:titulos_receber_list', slug=self.slug)