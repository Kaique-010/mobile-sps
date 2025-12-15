"""
Script de diagnóstico para problemas de permissões
Execute via: python manage.py shell < diagnostico_permissoes.py
"""
from django.contrib.contenttypes.models import ContentType
from perfilweb.models import Perfil, UsuarioPerfil, PermissaoPerfil, PerfilHeranca
from Licencas.models import Usuarios
from core.middleware import set_licenca_slug
from core.utils import get_db_from_slug

# Configure o slug da licença que quer diagnosticar
LICENCA_SLUG = 'casaa'  # ALTERE AQUI
USUARIO_TESTE_ID = 1  # ALTERE AQUI para o ID do usuário com problema

def diagnosticar():
    print("="*80)
    print("DIAGNÓSTICO DE PERMISSÕES")
    print("="*80)
    
    # Configurar contexto
    set_licenca_slug(LICENCA_SLUG)
    banco = get_db_from_slug(LICENCA_SLUG)
    
    print(f"\n✓ Licença: {LICENCA_SLUG}")
    print(f"✓ Banco: {banco}")
    
    # 1. Verificar usuário
    print(f"\n{'='*80}")
    print("1. VERIFICANDO USUÁRIO")
    print("="*80)
    
    try:
        usuario = Usuarios.objects.using(banco).get(usua_codi=USUARIO_TESTE_ID)
        print(f"✓ Usuário encontrado: {usuario.usua_nome} (ID: {usuario.usua_codi})")
    except Usuarios.DoesNotExist:
        print(f"✗ ERRO: Usuário ID {USUARIO_TESTE_ID} não encontrado!")
        return
    
    # 2. Verificar perfis do usuário
    print(f"\n{'='*80}")
    print("2. VERIFICANDO PERFIS DO USUÁRIO")
    print("="*80)
    
    rels = UsuarioPerfil.objects.using(banco).filter(
        perf_usua_id=USUARIO_TESTE_ID
    ).select_related('perf_perf')
    
    if not rels:
        print(f"✗ PROBLEMA: Usuário não tem nenhum perfil associado!")
        print(f"  Solução: Associe o usuário a um perfil ativo")
        return
    
    for rel in rels:
        perfil = rel.perf_perf
        status = "ATIVO" if rel.perf_ativ and perfil.perf_ativ else "INATIVO"
        print(f"  - Perfil: {perfil.perf_nome} (ID: {perfil.id}) - {status}")
        
        if not rel.perf_ativ:
            print(f"    ⚠ PROBLEMA: Relação usuário-perfil está INATIVA!")
        if not perfil.perf_ativ:
            print(f"    ⚠ PROBLEMA: Perfil está INATIVO!")
    
    # Pegar perfil ativo
    perfil_ativo = None
    for rel in rels:
        if rel.perf_ativ and rel.perf_perf.perf_ativ:
            perfil_ativo = rel.perf_perf
            break
    
    if not perfil_ativo:
        print(f"\n✗ PROBLEMA CRÍTICO: Nenhum perfil ATIVO encontrado!")
        print(f"  Solução: Ative um perfil ou a relação usuário-perfil")
        return
    
    print(f"\n✓ Perfil ativo selecionado: {perfil_ativo.perf_nome}")
    
    # 3. Verificar herança de perfis
    print(f"\n{'='*80}")
    print("3. VERIFICANDO HERANÇA DE PERFIS")
    print("="*80)
    
    herancas = PerfilHeranca.objects.using(banco).filter(perf_filho=perfil_ativo)
    
    if herancas:
        print(f"✓ Perfil herda de {herancas.count()} perfil(is) pai:")
        for h in herancas:
            print(f"  - {h.perf_pai.perf_nome} (ID: {h.perf_pai.id})")
        
        # Construir cadeia completa
        cadeia = [perfil_ativo.id]
        visitados = {perfil_ativo.id}
        pais = list(herancas.values_list('perf_pai_id', flat=True))
        
        while pais:
            novo = []
            for pid in pais:
                if pid in visitados:
                    continue
                cadeia.append(pid)
                visitados.add(pid)
                novo.extend(list(PerfilHeranca.objects.using(banco).filter(
                    perf_filho_id=pid
                ).values_list('perf_pai_id', flat=True)))
            pais = novo
        
        print(f"\n  Cadeia completa de herança: {cadeia}")
    else:
        print(f"  Perfil não herda de nenhum outro perfil")
        cadeia = [perfil_ativo.id]
    
    # 4. Verificar permissões
    print(f"\n{'='*80}")
    print("4. VERIFICANDO PERMISSÕES DO PERFIL")
    print("="*80)
    
    perms = PermissaoPerfil.objects.using(banco).filter(
        perf_perf_id__in=cadeia
    ).select_related('perf_ctype')
    
    total_perms = perms.count()
    print(f"✓ Total de permissões (incluindo herança): {total_perms}")
    
    if total_perms == 0:
        print(f"\n✗ PROBLEMA CRÍTICO: Perfil não tem NENHUMA permissão!")
        print(f"  Solução: Configure permissões para o perfil via interface admin")
        return
    
    # Agrupar por ContentType
    perms_por_ct = {}
    for perm in perms:
        ct = perm.perf_ctype
        key = f"{ct.app_label}.{ct.model}"
        if key not in perms_por_ct:
            perms_por_ct[key] = []
        perms_por_ct[key].append(perm.perf_acao)
    
    print(f"\nPermissões por recurso:")
    for recurso, acoes in sorted(perms_por_ct.items()):
        print(f"  {recurso}: {sorted(set(acoes))}")
    
    # 5. Verificar ContentTypes no banco
    print(f"\n{'='*80}")
    print("5. VERIFICANDO CONTENTTYPES DISPONÍVEIS")
    print("="*80)
    
    todos_cts = ContentType.objects.using(banco).all().order_by('app_label', 'model')
    
    print(f"✓ Total de ContentTypes no banco: {todos_cts.count()}")
    print(f"\nContentTypes relacionados a apps principais:")
    
    apps_interesse = ['pedidos', 'produtos', 'contas_a_pagar', 'contas_a_receber', 
                      'caixadiario', 'dre', 'perfilweb']
    
    for app in apps_interesse:
        cts_app = todos_cts.filter(app_label__icontains=app)
        if cts_app:
            print(f"\n  App: {app}")
            for ct in cts_app:
                tem_perm = f"{ct.app_label}.{ct.model}" in perms_por_ct
                status = "✓ TEM PERMISSÕES" if tem_perm else "✗ SEM PERMISSÕES"
                print(f"    - {ct.app_label}.{ct.model} (ID: {ct.id}) {status}")
    
    # 6. Teste de permissões específicas
    print(f"\n{'='*80}")
    print("6. TESTANDO PERMISSÕES ESPECÍFICAS")
    print("="*80)
    
    testes = [
        ('Pedidos', 'pedidovenda', 'listar'),
        ('Pedidos', 'pedidovenda', 'criar'),
        ('Produtos', 'produtos', 'listar'),
        ('contas_a_pagar', 'titulospagar', 'listar'),
        ('contas_a_receber', 'titulosreceber', 'listar'),
    ]
    
    from perfilweb.services import tem_permissao
    
    for app, model, acao in testes:
        resultado = tem_permissao(perfil_ativo, app, model, acao)
        status = "✓ PERMITIDO" if resultado else "✗ NEGADO"
        print(f"  {app}.{model} / {acao}: {status}")
    
    # 7. Recomendações
    print(f"\n{'='*80}")
    print("7. RECOMENDAÇÕES")
    print("="*80)
    
    if total_perms < 10:
        print("⚠ Perfil tem poucas permissões. Considere:")
        print("  - Verificar se as permissões foram salvas corretamente")
        print("  - Usar herança de perfis para simplificar gestão")
    
    # Verificar se apps comuns têm permissões
    apps_obrigatorios = ['Pedidos', 'Produtos']
    for app in apps_obrigatorios:
        tem = any(app.lower() in k.lower() for k in perms_por_ct.keys())
        if not tem:
            print(f"⚠ App '{app}' não tem permissões configuradas")
    
    print(f"\n✓ Diagnóstico concluído!")
    print(f"\nSe o problema persistir, ative o DEBUG e verifique os logs em:")
    print(f"  [perfil_services] e [perfil_mw]")

if __name__ == '__main__':
    diagnosticar()