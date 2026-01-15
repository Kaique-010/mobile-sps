from django.views.generic import FormView
from django.urls import reverse
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from django.contrib import messages
from rest_framework.permissions import IsAuthenticated
from core.registry import get_licenca_db_config
from core.middleware import get_licenca_slug
from Licencas.models import Filiais, Empresas, Usuarios
from Licencas.forms import FilialCertificadoForm,  EmpresaForm, FilialForm, UsuarioForm
from Licencas.crypto import encrypt_bytes, encrypt_str
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from Licencas.utils import get_proxima_filial, get_proxima_filial_empr, get_proxima_empresa, buscar_endereco_por_cep
from django.db.models import Max
from django.http import Http404, HttpResponseRedirect
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from  .utils import proximo_usuario, atualizar_senha


import logging
logger = logging.getLogger(__name__)

class FilialCertificadoUploadView(FormView):
    form_class = FilialCertificadoForm
    template_name = 'Licencas/filial_form.html'
    

    def form_valid(self, form):
        logger.info("Upload certificado iniciado")
        banco = get_licenca_db_config(self.request) or 'default'

        empresa_id = form.cleaned_data["empresa_id"]
        filial_id = form.cleaned_data["filial_id"]
        senha = form.cleaned_data["senha"]
        arquivo = form.cleaned_data["certificado"]
        logger.info(f"Upload certificado recebido para empresa {empresa_id}, filial {filial_id}")

        filial = Filiais.objects.using(banco).filter(
            empr_empr=empresa_id,
            empr_codi=filial_id
        ).first()

        if not filial:
            messages.error(self.request, "Filial não encontrada.")
            return self.form_invalid(form)

        conteudo = arquivo.read()
        logger.info(f"Certificado lido com {len(conteudo)} bytes")

        try:
            load_key_and_certificates(conteudo, senha.encode("utf-8"))
        except Exception as e:
            messages.error(self.request, "Certificado inválido ou senha incorreta.")
            return self.form_invalid(form)

        Filiais.objects.using(banco).filter(
            empr_empr=empresa_id,
            empr_codi=filial_id
        ).update(
            empr_cert=arquivo.name,
            empr_senh_cert=encrypt_str(senha),
            empr_cert_digi=encrypt_bytes(conteudo)
        )
        logger.info(f"Certificado salvo para empresa {empresa_id}, filial {filial_id}, tem {len(conteudo)} bytes, com a senha cifrada {encrypt_str(senha)}")

        messages.success(self.request, "Certificado salvo com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        slug = self.kwargs.get("slug")
        return reverse("filiais_web", kwargs={"slug": slug})

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

    def get_initial(self):
        initial = super().get_initial()
        # Valores SMTP padrão
        initial.update({
            'empr_smtp_host': 'smtp.savexml.com.br',
            'empr_smtp_port': '587',
            'empr_smtp_usua': 'notas@savexml.com.br',
            'empr_smtp_senh': 'sps@nfe',
            'empr_smtp_emai': 'notas@savexml.com.br',            
            'empr_cone_segu': True,
            'empr_tls': True,
            'empr_ssl': False,
            
        })
        return initial

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
        next_codi = ((Filiais.objects.using(self.db_alias)
                      .filter(empr_empr=int(empresa_id))
                      .aggregate(Max('empr_codi'))['empr_codi__max']) or 0) + 1
        obj.empr_codi = next_codi
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
        # Salva garantindo unicidade composta (empr_empr, empr_codi)
        from django.db import IntegrityError
        while True:
            try:
                obj.save(using=self.db_alias, force_insert=True)
                break
            except IntegrityError:
                next_codi = ((Filiais.objects.using(self.db_alias)
                              .filter(empr_empr=int(empresa_id))
                              .aggregate(Max('empr_codi'))['empr_codi__max']) or 0) + 1
                obj.empr_codi = next_codi
            except Exception:
                form.add_error(None, 'Falha ao salvar filial: verifique vínculos e chaves.')
                return self.form_invalid(form)
        # Garantir persistência explícita de campos de token
        Filiais.objects.using(self.db_alias).filter(empr_empr=obj.empr_empr, empr_codi=obj.empr_codi).update(
            empr_id_toke=form.cleaned_data.get('empr_id_toke'),
            empr_csn_toke=form.cleaned_data.get('empr_csn_toke')
        )
        messages.success(self.request, 'Filial criada com sucesso.')
        self.object = obj
        return HttpResponseRedirect(self.get_success_url())

    @action(detail=False, methods=['get'], url_path='buscar-endereco')
    def buscar_endereco(self, request, slug=None):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        
        cep = request.GET.get('cep')
        if not cep:
            return Response({"erro": "CEP não informado"}, status=400)

        # Cache para CEPs consultados
        cache_key = f"endereco_cep_{cep}"
        endereco = cache.get(cache_key)
        
        if not endereco:
            endereco = buscar_endereco_por_cep(cep)
            if endereco:
                cache.set(cache_key, endereco, 3600)  # Cache por 1 hora
        
        if endereco:
            return Response(endereco)
        else:
            return Response({"erro": "CEP inválido ou não encontrado"}, status=404)


class FilialUpdateView(DBSlugMixin, UpdateView):
    model = Filiais
    form_class = FilialForm
    template_name = 'Licencas/filial_form.html'
    pk_url_kwarg = 'empr_empr'

    def get_queryset(self):
        return Filiais.objects.using(self.db_alias)

    def get_object(self, queryset=None):
        qs = queryset or self.get_queryset()
        empresa = int(self.kwargs.get(self.pk_url_kwarg))
        filial = self.request.GET.get('filial_id')

        if not filial:
            raise Http404("Parâmetro 'filial_id' é obrigatório.")

        try:
            filial = int(filial)
        except ValueError:
            raise Http404("filial_id inválido.")

        obj = qs.filter(empr_empr=empresa, empr_codi=filial).first()
        if not obj:
            raise Http404("Filial não encontrada.")
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["certificado_form"] = FilialCertificadoForm(initial={
            "empresa_id": self.object.empr_empr,
            "filial_id": self.object.empr_codi,
        })

        return ctx

    def form_valid(self, form):
        # Salvar apenas os campos NORMAIS da Filial
        filial = form.save(commit=False)
        Filiais.objects.using(self.db_alias).filter(
            empr_empr=filial.empr_empr,
            empr_codi=filial.empr_codi
        ).update(**{
            field: getattr(filial, field)
            for field in form.cleaned_data.keys()
            if field in [f.name for f in Filiais._meta.fields]
        })

        messages.success(self.request, "Filial atualizada com sucesso.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("filiais_web", kwargs={"slug": self.slug})


class RoleRequiredMixin:
    allowed_roles = ('admin', 'mobile')

    def dispatch(self, request, *args, **kwargs):
        import logging
        banco = get_licenca_db_config(request)
        setattr(request, 'db_alias', banco)
        self.db_alias = banco
        log = logging.getLogger(__name__)
        raw_user = getattr(request, 'user', None)
        username_guess = (getattr(raw_user, 'usua_nome', '') or getattr(raw_user, 'username', '') or '').lower()
        db_user = None
        try:
            if hasattr(raw_user, 'usua_codi') and raw_user.usua_codi:
                db_user = Usuarios.objects.using(self.db_alias).filter(usua_codi=raw_user.usua_codi).first()
            elif username_guess:
                db_user = Usuarios.objects.using(self.db_alias).filter(usua_nome__iexact=username_guess).first()
        except Exception:
            db_user = None
        username = (getattr(db_user, 'usua_nome', '') or username_guess or '').lower()
        role = username if username in {r.lower() for r in self.allowed_roles} else 'regular'
        user_id = getattr(db_user, 'usua_codi', None) or getattr(raw_user, 'usua_codi', None)
        log.info(f"[ACCESS] path={request.path} role={role} user_id={user_id}")
        if role not in {r.lower() for r in self.allowed_roles}:
            messages.error(request, 'Acesso negado: você não possui permissão para esta ação.')
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(reverse('home'))
        return super().dispatch(request, *args, **kwargs)


class UserListView(RoleRequiredMixin, DBSlugMixin, ListView):
    model = Usuarios
    template_name = 'Licencas/usuarios_lista.html'
    context_object_name = 'usuarios'
    

    def get_queryset(self):
        qs = Usuarios.objects.using(self.db_alias).order_by('-usua_codi')
        nome = (self.request.GET.get('nome') or '').strip()
        if nome:
            qs = qs.filter(usua_nome__icontains=nome)
        return qs.order_by('usua_nome')


class UserCreateView(RoleRequiredMixin, DBSlugMixin, CreateView):
    model= Usuarios
    form_class = UsuarioForm
    template_name = 'Licencas/usuario_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        logger.info("[UserCreate] Início form_valid alias=%s", self.db_alias)
        logger.debug("[UserCreate] cleaned_data=%s", dict(form.cleaned_data))
        usuario = form.save(commit=False)
        # Gerar próximo código de usuário
        usuario.usua_codi = proximo_usuario(self.request)
        try:
            logger.info("[UserCreate] Salvando usuario nome=%s codi=%s", usuario.usua_nome, usuario.usua_codi)
            usuario.save(using=self.db_alias, force_insert=True)
            try:
                nova = (form.cleaned_data.get('password') or '').strip()
                if nova:
                    atualizar_senha(usuario.usua_nome, nova, request=self.request)
            except Exception:
                pass
        except Exception:
            logger.exception("[UserCreate] Erro ao salvar usuário")
            form.add_error(None, 'Falha ao criar usuário. Verifique os dados informados.')
            messages.error(self.request, 'Falha ao criar usuário. Verifique os dados informados.')
            return self.form_invalid(form)
        messages.success(self.request, "Usuário criado com sucesso.")
        logger.info("[UserCreate] Concluído com sucesso usua_codi=%s", usuario.usua_codi)
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        logger.warning("[UserCreate] FORM INVALID errors=%s", form.errors)
        messages.error(self.request, 'Corrija os erros para continuar.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('users_list', kwargs={'slug': self.slug})

class UserEditView(RoleRequiredMixin, DBSlugMixin, UpdateView):
    model = Usuarios
    form_class = UsuarioForm
    template_name = 'Licencas/usuario_form.html'
    pk_url_kwarg = 'id'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_queryset(self):
        return Usuarios.objects.using(self.db_alias)

    def get_object(self, queryset=None):
        qs = queryset or self.get_queryset()
      
        user_id = self.kwargs.get(self.pk_url_kwarg)
        try:
            user_id = int(user_id)
        except Exception:
            raise Http404('Parâmetro inválido.')
        obj = qs.filter(usua_codi=user_id).first()
        if not obj:
            raise Http404('Usuário não encontrado.')
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["usuario_id"] = self.object.usua_codi
        return ctx
    
    def form_valid(self, form):
        logger.info("[UserEdit] Início form_valid alias=%s", self.db_alias)
        logger.debug("[UserEdit] cleaned_data=%s", dict(form.cleaned_data))
        usuario = form.save(commit=False)
        
        try:
            nova = (form.cleaned_data.get('password') or '').strip()
            if not nova:
                try:
                    antigo = Usuarios.objects.using(self.db_alias).filter(usua_codi=usuario.usua_codi).values_list('password', flat=True).first()
                    if antigo:
                        usuario.password = antigo
                except Exception:
                    pass
            logger.info("[UserEdit] Salvando usuario nome=%s codi=%s", usuario.usua_nome, usuario.usua_codi)
            usuario.save(using=self.db_alias)
            try:
                if nova:
                    atualizar_senha(usuario.usua_nome, nova, request=self.request)
            except Exception:
                pass
        except Exception:
            logger.exception("[UserEdit] Erro ao atualizar usuário")
            form.add_error(None, 'Falha ao atualizar usuário.')
            messages.error(self.request, 'Falha ao atualizar usuário.')
            return self.form_invalid(form)
        messages.success(self.request, "Usuário atualizado com sucesso.")
        logger.info("[UserEdit] Concluído com sucesso usua_codi=%s", usuario.usua_codi)
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        logger.warning("[UserEdit] FORM INVALID errors=%s", form.errors)
        messages.error(self.request, 'Corrija os erros para continuar.')
        return super().form_invalid(form)
    def get_success_url(self):
        return reverse_lazy('users_list', kwargs={'slug': self.slug})

class UserDeleteView(RoleRequiredMixin, DBSlugMixin, FormView):
    template_name = 'Licencas/usuario_confirm_delete.html'

    def post(self, request, *args, **kwargs):
        logger.info('[UserDelete] Solicitação de exclusão alias=%s', self.db_alias)
        user_id = kwargs.get('id')
        try:
            user_id = int(user_id)
        except Exception:
            logger.warning('[UserDelete] ID inválido: %s', user_id)
            messages.error(request, 'ID inválido.')
            return HttpResponseRedirect(reverse('users_list', kwargs={'slug': self.slug}))
        try:
            logger.info('[UserDelete] Excluindo usuario id=%s', user_id)
            Usuarios.objects.using(self.db_alias).filter(usua_codi=user_id).delete()
            messages.success(request, 'Usuário excluído com sucesso.')
        except Exception:
            logger.exception('[UserDelete] Falha ao excluir usuario id=%s', user_id)
            messages.error(request, 'Falha ao excluir usuário.')
        return HttpResponseRedirect(reverse('users_list', kwargs={'slug': self.slug}))
