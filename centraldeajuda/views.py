# central/views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from .models import CentralDeAjuda, CentralProgresso
from .forms import CentralDeAjudaForm
from core.utils import get_db_from_slug
from Licencas.models import Usuarios
from Licencas.web_views import DBSlugMixin, RoleRequiredMixin
from django.db.models import OuterRef, Subquery, IntegerField, CharField, Value, Case, When
from django.db.models.functions import Coalesce

class CentralListView(DBSlugMixin, ListView):
    model = CentralDeAjuda
    template_name = "centraldeajuda/lista.html"

    def get_queryset(self):
        db_alias = get_db_from_slug('save1') or 'savexml1'
        banco = self.request.session.get("empresa_id")
        usuario_obj = None
        try:
            usuario_id = (
                self.request.session.get('usuario_id')
                or self.request.headers.get('usuario_id')
                or self.request.headers.get('X-Usuario')
            )
            if usuario_id and db_alias:
                usuario_obj = Usuarios.objects.using(db_alias).filter(usua_codi=int(usuario_id)).first()
            if not usuario_obj and hasattr(self.request, 'user'):
                nome_auth = getattr(self.request.user, 'usua_nome', None) or getattr(self.request.user, 'username', None)
                if nome_auth and db_alias:
                    usuario_obj = Usuarios.objects.using(db_alias).filter(usua_nome__iexact=str(nome_auth)).first()
        except Exception:
            usuario_obj = None

        qs = (
            CentralDeAjuda.objects.using(db_alias)
            .filter(cent_empr=banco)
            .order_by("cent_modu", "-cent_data_cria")
        )

        if usuario_obj:
            subq = CentralProgresso.objects.using(db_alias).filter(
                usuario=usuario_obj,
                ajuda_id=OuterRef('pk')
            ).values('progresso')[:1]
            qs = qs.annotate(prog=Coalesce(Subquery(subq, output_field=IntegerField()), Value(0)))
        else:
            qs = qs.annotate(prog=Value(0, output_field=IntegerField()))

        qs = qs.annotate(
            status=Case(
                When(prog__gte=100, then=Value('Concluído')),
                When(prog__gt=0, then=Value('Em andamento')),
                default=Value('Não iniciado'),
                output_field=CharField(),
            ),
            status_class=Case(
                When(prog__gte=100, then=Value('success')),
                When(prog__gt=0, then=Value('primary')),
                default=Value('secondary'),
                output_field=CharField(),
            ),
        )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        objetos = ctx.get('object_list') or []
        modulo_media = {}
        modulo_contagem = {}
        for obj in objetos:
            prog = getattr(obj, 'prog', None)
            prog = prog if isinstance(prog, int) else 0
            codigo = obj.cent_modu
            modulo_media[codigo] = modulo_media.get(codigo, 0) + prog
            modulo_contagem[codigo] = modulo_contagem.get(codigo, 0) + 1

        # Monta cards de módulos com média de progresso
        choices_map = dict(CentralDeAjuda.MODULOS)
        module_cards = []
        for codigo, total in modulo_media.items():
            count = modulo_contagem.get(codigo, 1)
            avg = round(total / max(count, 1))
            module_cards.append({
                'code': codigo,
                'name': choices_map.get(codigo, codigo),
                'count': count,
                'avg': avg,
            })

        # Garante slug no contexto
        try:
            ctx['slug'] = self.slug
        except Exception:
            pass

        ctx['module_cards'] = module_cards
        return ctx


class CentralDetailView(LoginRequiredMixin, DBSlugMixin, DetailView):
    model = CentralDeAjuda
    template_name = "centraldeajuda/detalhe.html"

    def get_queryset(self):
        db_alias = get_db_from_slug('save1') or 'savexml1'
        banco = self.request.session.get("empresa_id")
        return CentralDeAjuda.objects.using(db_alias).filter(cent_empr=banco)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            ctx['slug'] = self.slug
        except Exception:
            pass
        return ctx


class CentralCreateView(LoginRequiredMixin, RoleRequiredMixin, DBSlugMixin, CreateView):
    model = CentralDeAjuda
    form_class = CentralDeAjudaForm
    template_name = "centraldeajuda/form.html"
    allowed_roles = ('admin', 'mobile')

    def get_success_url(self):
        return reverse_lazy("central_lista", kwargs={"slug": self.slug})

    def form_valid(self, form):
        form.instance.cent_empr = self.request.session.get("empresa_id")
        banco = get_db_from_slug('save1') or 'savexml1'
        usuario_obj = None
        try:
            usuario_id = (
                self.request.session.get('usuario_id')
                or self.request.headers.get('usuario_id')
                or self.request.headers.get('X-Usuario')
            )
            if usuario_id and banco:
                usuario_obj = Usuarios.objects.using(banco).filter(usua_codi=int(usuario_id)).first()
            if not usuario_obj:
                nome = (
                    (self.request.session.get('usuario_nome') or self.request.session.get('usua_nome') or '')
                    or (self.request.headers.get('X-Usuario-Nome') or self.request.headers.get('X-Usuario') or '')
                ).strip()
                if nome:
                    usuario_obj = Usuarios.objects.using(banco).filter(usua_nome__iexact=nome).first()
            # Fallback: tenta mapear pelo usuário autenticado
            if not usuario_obj and hasattr(self.request, 'user'):
                try:
                    nome_auth = getattr(self.request.user, 'usua_nome', None) or getattr(self.request.user, 'username', None)
                    if nome_auth and banco:
                        usuario_obj = Usuarios.objects.using(banco).filter(usua_nome__iexact=str(nome_auth)).first()
                except Exception:
                    pass
        except Exception:
            usuario_obj = None
        # Último fallback para evitar violação NOT NULL
        if not usuario_obj and banco:
            try:
                usuario_obj = Usuarios.objects.using(banco).first()
            except Exception:
                usuario_obj = None
        form.instance.cent_usua_crio = usuario_obj
        obj = form.save(commit=False)
        obj.save(using=banco)
        return super().form_valid(form)


class CentralUpdateView(LoginRequiredMixin, RoleRequiredMixin, DBSlugMixin, UpdateView):
    model = CentralDeAjuda
    form_class = CentralDeAjudaForm
    template_name = "centraldeajuda/form.html"
    allowed_roles = ('admin', 'mobile')

    def get_success_url(self):
        return reverse_lazy("central_lista", kwargs={"slug": self.slug})

    def get_queryset(self):
        db_alias = get_db_from_slug('save1') or 'savexml1'
        banco = self.request.session.get("empresa_id")
        return CentralDeAjuda.objects.using(db_alias).filter(cent_empr=banco)

    def form_valid(self, form):
        banco = get_db_from_slug('save1') or 'savexml1'
        obj = form.save(commit=False)
        obj.save(using=banco)
        return super().form_valid(form)
