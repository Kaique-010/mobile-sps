from django.views.generic import TemplateView, View
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.core.cache import cache
from core.decorator import ModuloRequeridoMixin
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from .models import Modulo, PermissaoModulo
import logging

logger = logging.getLogger(__name__)


def _resolve_empresa_filial(request):
    def _to_int(v, default=None):
        try:
            return int(v)
        except (TypeError, ValueError):
            return default
    empresa = _to_int(request.headers.get('X-Empresa')) \
              or _to_int(request.POST.get('empresa_id')) \
              or request.session.get('empresa_id') \
              or _to_int(getattr(request.user, 'usua_empr', None), 1) \
              or 1
    filial = _to_int(request.headers.get('X-Filial')) \
             or _to_int(request.POST.get('filial_id')) \
             or request.session.get('filial_id') \
             or _to_int(getattr(request.user, 'usua_fili', None), 1) \
             or 1
    return empresa, filial


class ModulosListView(ModuloRequeridoMixin, TemplateView):
  
    template_name = 'ParametrosAdmin/modulos_list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request)
        slug = kwargs.get('slug') or get_licenca_slug() or self.request.session.get('slug')
        empresa_id, filial_id = _resolve_empresa_filial(self.request)

        modulos = list(Modulo.objects.using(banco).all().order_by('modu_orde', 'modu_nome'))
        liberados = set(PermissaoModulo.objects.using(banco).filter(
            perm_empr=empresa_id,
            perm_fili=filial_id,
            perm_ativ=True
        ).values_list('perm_modu__modu_nome', flat=True))

        itens = []
        for m in modulos:
            itens.append({
                'slug': m.modu_nome,
                'nome': m.modu_nome,
                'desc': m.modu_desc,
                'icone': m.modu_icon,
                'ativo_global': m.modu_ativ,
                'permitido': m.modu_nome in liberados,
            })

        ctx.update({
            'slug': slug,
            'empresa_id': empresa_id,
            'filial_id': filial_id,
            'modulos': itens,
        })
        return ctx


class ModuloToggleView(ModuloRequeridoMixin, View):
  

    def post(self, request, slug, modulo_slug):
        banco = get_licenca_db_config(request)
        empresa_id, filial_id = _resolve_empresa_filial(request)
        slug = slug or get_licenca_slug() or request.session.get('slug')

        try:
            modulo = Modulo.objects.using(banco).get(modu_nome=modulo_slug)
        except Modulo.DoesNotExist:
            messages.error(request, f'Módulo "{modulo_slug}" não encontrado')
            return redirect(reverse('parametros_admin_modulos', kwargs={'slug': slug}))

        perm, created = PermissaoModulo.objects.using(banco).get_or_create(
            perm_empr=empresa_id,
            perm_fili=filial_id,
            perm_modu=modulo,
            defaults={'perm_ativ': True, 'perm_usua_libe': getattr(request.user, 'usua_codi', 0)}
        )

        if not created:
            novo_estado = not perm.perm_ativ
            atualizados = PermissaoModulo.objects.using(banco).filter(
                perm_empr=empresa_id,
                perm_fili=filial_id,
                perm_modu=modulo,
            ).update(
                perm_ativ=novo_estado,
                perm_usua_libe=getattr(request.user, 'usua_codi', 0)
            )
            try:
                logger.info(f"Permissão atualizada para módulo {modulo.modu_nome} no banco {banco}: {atualizados} linha(s), estado={novo_estado}")
            except Exception:
                pass

        # limpar cache de módulos para refletir imediatamente
        cache_key = f"modulos_licenca_{slug}_{empresa_id}_{filial_id}"
        cache.delete(cache_key)

        messages.success(request, f'Permissão do módulo "{modulo.modu_nome}" atualizada')
        return redirect(reverse('parametros_admin_modulos', kwargs={'slug': slug}))

class ModulosSyncView(ModuloRequeridoMixin, View):
  

    def post(self, request, slug):
        banco = get_licenca_db_config(request)
        Modulo.sync_installed_apps(alias=banco, force=True)
        empresa_id, filial_id = _resolve_empresa_filial(request)
        from .utils import sync_permissoes_com_modulos
        criadas, existentes = sync_permissoes_com_modulos(
            banco,
            empresa_id,
            filial_id,
            usuario_id=getattr(request.user, 'usua_codi', 0),
            default_ativ=False,
        )
        created, updated = 0, 0
        for modulo in Modulo.objects.using(banco).all().order_by('modu_orde', 'modu_nome'):
            perm, was_created = PermissaoModulo.objects.using(banco).get_or_create(
                perm_empr=empresa_id,
                perm_fili=filial_id,
                perm_modu=modulo,
                defaults={'perm_ativ': True, 'perm_usua_libe': getattr(request.user, 'usua_codi', 0)}
            )
            if was_created:
                created += 1
            else:
                if perm.perm_ativ is False:
                    perm.perm_ativ = True
                    perm.perm_usua_libe = getattr(request.user, 'usua_codi', 0)
                    perm.save(using=banco)
                    updated += 1
        cache.delete(f"modulos_licenca_{slug}_{empresa_id}_{filial_id}")
        messages.success(request, f'Módulos sincronizados: {created} criados, {updated} reativados; permissões criadas: {criadas}')
        return redirect(reverse('parametros_admin_modulos', kwargs={'slug': slug}))
