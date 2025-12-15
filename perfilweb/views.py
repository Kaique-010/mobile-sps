from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.db.models import Count, Q
from .models import Perfil, PerfilHeranca, PermissaoPerfil, UsuarioPerfil
from Licencas.models import Usuarios
from .sync import listar_recursos, sincronizar_permissoes_padrao, criar_perfis_padrao, aplicar_permissoes_padrao_por_perfil, bootstrap_inicial
from .permission_service import salvar_permissoes, salvar_herancas
from .services import tem_permissao
from core.middleware import get_licenca_slug
from core.utils import get_db_from_slug


class PerfisListView(View):
    def get(self, request, slug=None):
        banco = get_db_from_slug(get_licenca_slug())
        perfis = (
            Perfil.objects.using(banco)
            .filter(perf_ativ=True)
            .annotate(
                usuarios_count=Count('usuarioperfil', filter=Q(usuarioperfil__perf_ativ=True), distinct=True),
                permissoes_count=Count('permissaoperfil', distinct=True),
                pais_count=Count('perf_pais_rel', distinct=True),
            )
            .order_by('perf_nome')
        )
        return render(request, 'perfil/lista.html', {'perfis': perfis, 'slug': slug})


class PerfilPermissaoView(View):

    def get(self, request, slug=None, perfil_id=None):
        banco = get_db_from_slug(get_licenca_slug())
        perfil = get_object_or_404(Perfil.objects.using(banco), id=perfil_id)
        recursos = listar_recursos()

        qs_perms = PermissaoPerfil.objects.using(banco).filter(perf_perf=perfil)
        permissoes_atuais = {(p.perf_ctype_id, p.perf_acao) for p in qs_perms}
        permissoes_atuis_keys_qs = PermissaoPerfil.objects.using(banco).filter(perf_perf=perfil).values_list('perf_ctype_id', 'perf_acao')
        permissoes_atuais_keys = {f"{cid}:{acao}" for cid, acao in permissoes_atuis_keys_qs}
        pais_atuais = list(PerfilHeranca.objects.using(banco).filter(perf_filho=perfil).values_list('perf_pai_id', flat=True))
        todos_perfis = Perfil.objects.using(banco).filter(perf_ativ=True).exclude(id=perfil.id).order_by('perf_nome')
        usuarios_all = Usuarios.objects.using(banco).all().order_by('usua_nome')
        usuarios_atuais = list(UsuarioPerfil.objects.using(banco).filter(perf_perf=perfil, perf_ativ=True).values_list('perf_usua_id', flat=True))

        return render(request, 'perfil/permissoes.html', {
            'perfil': perfil,
            'recursos': recursos,
            'permissoes_atuais': permissoes_atuais,
            'permissoes_atuais_keys': permissoes_atuais_keys,
            'slug': slug,
            'pais_atuais': pais_atuais,
            'todos_perfis': todos_perfis,
            'usuarios_all': usuarios_all,
            'usuarios_atuais': usuarios_atuais,
        })

    def post(self, request, slug=None, perfil_id=None):
        banco = get_db_from_slug(get_licenca_slug())
        perfil = get_object_or_404(Perfil.objects.using(banco), id=perfil_id)

        payload = {}
        for key in request.POST:
            if not key.startswith('perm_'):
                continue
            _, ct_id, acao = key.split('_')
            payload.setdefault(int(ct_id), []).append(acao)

        salvar_permissoes(perfil, payload, operador=request.user)
        pais = request.POST.getlist('heranca')
        salvar_herancas(perfil, pais)
        usuarios = request.POST.getlist('usuarios')
        from .permission_service import salvar_usuarios_perfil
        salvar_usuarios_perfil(perfil, usuarios)

        return redirect('perfil_permissoes', slug=slug, perfil_id=perfil.id)


def recursos_api(request, slug=None):
    return JsonResponse({'recursos': listar_recursos()})


def verificar_api(request, slug=None):
    banco = get_db_from_slug(get_licenca_slug())
    perfil_id = int(request.GET.get('perfil_id'))
    app_label = request.GET.get('app_label')
    model = request.GET.get('model')
    acao = request.GET.get('acao')
    perfil = get_object_or_404(Perfil.objects.using(banco), id=perfil_id)
    ok = tem_permissao(perfil, app_label, model, acao)
    return JsonResponse({'permitido': ok})


def sincronizar_api(request, slug=None):
    criados = sincronizar_permissoes_padrao()
    return JsonResponse({'criados': criados})


def perfis_defaults_api(request, slug=None):
    criados_count, perfis = criar_perfis_padrao()
    aplicados = {}
    for p in perfis:
        aplicados[p.perf_nome] = aplicar_permissoes_padrao_por_perfil(p)
    return JsonResponse({'criados': criados_count, 'aplicados': aplicados})


def aplicar_defaults_api(request, perfil_id, slug=None):
    banco = get_db_from_slug(get_licenca_slug())
    perfil = get_object_or_404(Perfil.objects.using(banco), id=perfil_id)
    count = aplicar_permissoes_padrao_por_perfil(perfil)
    return JsonResponse({'perfil': perfil.perf_nome, 'aplicados': count})


def bootstrap_api(request, slug=None):
    result = bootstrap_inicial()
    return JsonResponse(result)
