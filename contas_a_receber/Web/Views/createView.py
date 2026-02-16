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
        empresa = (self.request.session.get('empresa_id')
               or self.request.headers.get('X-Empresa')
               or self.request.GET.get('titu_empr')
               or getattr(self, 'empresa_id', None))
        filial = (self.request.session.get('filial_id')
               or self.request.headers.get('X-Filial')
               or self.request.GET.get('titu_fili')
               or getattr(self, 'filial_id', None))
        if empresa is not None:
            try:
                dados['titu_empr'] = int(empresa)
            except Exception:
                dados['titu_empr'] = empresa
        if filial is not None:
            try:
                dados['titu_fili'] = int(filial)
            except Exception:
                dados['titu_fili'] = filial
        from ...services import criar_titulo_receber, gera_parcelas_a_receber
        self.object = criar_titulo_receber(
            banco=banco,
            dados=dados,
            empresa_id=(dados.get('titu_empr') or empresa),
            filial_id=(dados.get('titu_fili') or filial)
        )
        gera_parcelas_a_receber(
            titulo=self.object,
            banco=banco,
        )
        return redirect('contas_a_receber_web:titulos_receber_list', slug=self.slug)


class TitulosReceberParcelasCreateView(DBAndSlugMixin, CreateView):
    model = Titulosreceber
    form_class = TitulosReceberForm
    template_name = 'ContasAReceber/parcelas_receber_criar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = self.object
        return context
    
    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        dados = form.cleaned_data
        empresa = (self.request.session.get('empresa_id')
               or self.request.headers.get('X-Empresa')
               or self.request.GET.get('titu_empr')
               or getattr(self, 'empresa_id', None))
        filial = (self.request.session.get('filial_id')
               or self.request.headers.get('X-Filial')
               or self.request.GET.get('titu_fili')
               or getattr(self, 'filial_id', None))
        if empresa is not None:
            try:
                dados['titu_empr'] = int(empresa)
            except Exception:
                dados['titu_empr'] = empresa
        if filial is not None:
            try:
                dados['titu_fili'] = int(filial)
            except Exception:
                dados['titu_fili'] = filial
        from ...services import criar_titulo_receber, gera_parcelas_a_receber
        self.object = criar_titulo_receber(
            banco=banco,
            dados=dados,
            empresa_id=(dados.get('titu_empr') or empresa),
            filial_id=(dados.get('titu_fili') or filial)
        )
        gera_parcelas_a_receber(
            titulo=self.object,
            banco=banco,
        )
        print("criação de parcelas a recebert:", self.object)
        return redirect('contas_a_receber_web:parcelas_a_receber_list', slug=self.slug)
