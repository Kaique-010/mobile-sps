from django.views.generic import FormView
from django.urls import reverse
from django.contrib import messages
from rest_framework.permissions import IsAuthenticated
from Licencas.forms import FilialCertificadoForm
from core.registry import get_licenca_db_config
from core.middleware import get_licenca_slug
from Licencas.models import Filiais
from Licencas.crypto import encrypt_bytes, encrypt_str
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from Licencas.utils import get_proxima_filial, get_proxima_filial_empr, get_proxima_empresa
from django.db.models import Max
from django.http import Http404

class FilialCertificadoUploadView(FormView):
    template_name = 'Licencas/filial_certificado_form.html'
    form_class = FilialCertificadoForm

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request)
        empresa_id = form.cleaned_data['empresa_id']
        filial_id = form.cleaned_data['filial_id']
        senha = form.cleaned_data['senha']
        arquivo = form.cleaned_data['certificado']
        filial = Filiais.objects.using(banco).filter(empr_empr=filial_id, empr_codi=empresa_id).first()
        if not filial:
            messages.error(self.request, 'Filial não encontrada.')
            return self.form_invalid(form)
        conteudo = arquivo.read()
        try:
            load_key_and_certificates(conteudo, senha.encode('utf-8'))
        except Exception:
            messages.error(self.request, 'Certificado inválido ou senha incorreta.')
            return self.form_invalid(form)
        filial.empr_cert = getattr(arquivo, 'name', 'certificado.p12')
        filial.empr_senh_cert = encrypt_str(senha)
        filial.empr_cert_digi = encrypt_bytes(conteudo)
        filial.save(using=banco)
        messages.success(self.request, 'Certificado salvo com sucesso.')
        return super().form_valid(form)

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return reverse('web_licencas_certificado', kwargs={'slug': slug})

from django.views.generic import ListView, CreateView, UpdateView
from Licencas.models import Empresas
from Licencas.forms import EmpresaForm, FilialForm
from django.urls import reverse_lazy

class DBSlugMixin:
    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug') or get_licenca_slug()
        self.db_alias = get_licenca_db_config(request)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = getattr(self, 'slug', None)
        return ctx

class EmpresaListView(DBSlugMixin, ListView):
    model = Empresas
    template_name = 'Licencas/empresas_lista.html'
    context_object_name = 'empresas'

    def get_queryset(self):
        return Empresas.objects.using(self.db_alias).all()

class EmpresaCreateView(DBSlugMixin, CreateView):
    model = Empresas
    form_class = EmpresaForm
    template_name = 'Licencas/empresa_form.html'

    def get_success_url(self):
        return reverse_lazy('empresas_web', kwargs={'slug': self.slug})

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.empr_codi = get_proxima_empresa(self.db_alias)
        obj.save(using=self.db_alias)
        messages.success(self.request, 'Empresa criada com sucesso.')
        return super().form_valid(form)

class EmpresaUpdateView(DBSlugMixin, UpdateView):
    model = Empresas
    form_class = EmpresaForm
    template_name = 'Licencas/empresa_form.html'
    pk_url_kwarg = 'empr_codi'

    def get_queryset(self):
        return Empresas.objects.using(self.db_alias).all()

    def get_success_url(self):
        return reverse_lazy('empresas_web', kwargs={'slug': self.slug})

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.save(using=self.db_alias)
        messages.success(self.request, 'Empresa atualizada com sucesso.')
        return super().form_valid(form)

class FilialListView(DBSlugMixin, ListView):
    model = Filiais
    template_name = 'Licencas/filiais_lista.html'
    context_object_name = 'filiais'

    def get_queryset(self):
        empresa_id = self.request.GET.get('empresa_id')
        qs = Filiais.objects.using(self.db_alias).all()
        if empresa_id:
            qs = qs.filter(empr_empr=int(empresa_id))
        return qs

class FilialCreateView(DBSlugMixin, CreateView):
    model = Filiais
    form_class = FilialForm
    template_name = 'Licencas/filial_form.html'

    def get_success_url(self):
        return reverse_lazy('filiais_web', kwargs={'slug': self.slug})

    def form_valid(self, form):
        obj = form.save(commit=False)
        empresa_id = self.request.GET.get('empresa_id') or self.request.POST.get('empresa_id')
        if not empresa_id:
            from Licencas.models import Empresas
            empresa = Empresas.objects.using(self.db_alias).order_by('empr_codi').first()
            if not empresa:
                form.add_error(None, 'Nenhuma empresa encontrada para vincular a filial.')
                return self.form_invalid(form)
            empresa_id = empresa.empr_codi
        obj.empr_empr = int(empresa_id)
        obj.empr_codi = ((Filiais.objects.using(self.db_alias)
                           .filter(empr_empr=int(empresa_id))
                           .aggregate(Max('empr_codi'))['empr_codi__max']) or 0) + 1
        senha = form.cleaned_data.get('senha_certificado')
        arquivo = form.cleaned_data.get('certificado')
        if senha:
            obj.empr_senh_cert = encrypt_str(senha)
        if arquivo:
            content = arquivo.read()
            try:
                load_key_and_certificates(content, (senha or '').encode('utf-8'))
            except Exception:
                form.add_error('certificado', 'Certificado inválido ou senha incorreta.')
                return self.form_invalid(form)
            obj.empr_cert = getattr(arquivo, 'name', 'certificado.p12')
            obj.empr_cert_digi = encrypt_bytes(content)
        try:
            obj.save(using=self.db_alias, force_insert=True)
        except Exception as e:
            form.add_error(None, 'Falha ao salvar filial: verifique vínculos e chaves.')
            return self.form_invalid(form)
        messages.success(self.request, 'Filial criada com sucesso.')
        return super().form_valid(form)

class FilialUpdateView(DBSlugMixin, UpdateView):
    model = Filiais
    form_class = FilialForm
    template_name = 'Licencas/filial_form.html'
    pk_url_kwarg = 'empr_empr'

    def get_queryset(self):
        return Filiais.objects.using(self.db_alias).all()

    def get_object(self, queryset=None):
        qs = queryset or self.get_queryset()
        empresa = int(self.kwargs.get(self.pk_url_kwarg))
        filial = self.request.GET.get('filial_id')
        if not filial:
            raise Http404('Parâmetro "filial_id" é obrigatório para editar a filial.')
        try:
            filial = int(filial)
        except ValueError:
            raise Http404('Parâmetro "filial_id" inválido.')
        obj = qs.filter(empr_empr=empresa, empr_codi=filial).first()
        if not obj:
            raise Http404('Filial não encontrada para a empresa informada.')
        return obj

    def get_initial(self):
        initial = super().get_initial()
        initial['senha_certificado'] = '********' if self.object and self.object.empr_senh_cert else ''
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['has_cert'] = bool(self.object and self.object.empr_cert_digi)
        ctx['cert_name'] = self.object.empr_cert if self.object else ''
        return ctx

    def get_success_url(self):
        return reverse_lazy('filiais_web', kwargs={'slug': self.slug})

    def form_valid(self, form):
        obj = form.save(commit=False)
        senha = form.cleaned_data.get('senha_certificado')
        arquivo = form.cleaned_data.get('certificado')
        if not obj.empr_empr:
            empresa_id = self.request.GET.get('empresa_id') or self.request.POST.get('empresa_id')
            if empresa_id:
                obj.empr_empr = int(empresa_id)
        if senha and senha != '********':
            obj.empr_senh_cert = encrypt_str(senha)
        if arquivo:
            content = arquivo.read()
            try:
                load_key_and_certificates(content, (senha or '').encode('utf-8'))
            except Exception:
                form.add_error('certificado', 'Certificado inválido ou senha incorreta.')
                return self.form_invalid(form)
            obj.empr_cert = getattr(arquivo, 'name', 'certificado.p12')
            obj.empr_cert_digi = encrypt_bytes(content)
        obj.save(using=self.db_alias)
        messages.success(self.request, 'Filial atualizada com sucesso.')
        return super().form_valid(form)
