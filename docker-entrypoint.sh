#!/bin/bash
set -e

# --- Aguardar Redis estar disponível ---
echo "Aguardando Redis..."
while ! nc -z redis 6379; do
  sleep 0.5
done
echo "Redis disponível!"

# --- Executar migrações ---
echo "Executando migrações..."
python manage.py migrate --noinput

# --- Coletar arquivos estáticos ---
echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --clear

# --- PRÉ-AQUECIMENTO AGRESSIVO PARA LOGIN INSTANTÂNEO ---
echo "🔥 Pré-aquecimento agressivo para login instantâneo..."
python manage.py shell -c "
import django
import time
from django.db import connection, connections
from django.core.cache import cache
from Licencas.models import Licencas, Usuarios, Empresas, Filiais
from parametros_admin.models import Modulo, PermissaoModulo

print('🚀 INICIANDO PRÉ-AQUECIMENTO ULTRA-RÁPIDO')
start_time = time.time()

# 1. Aquecer TODAS as conexões do pool
print('⚡ Aquecendo pool de conexões...')
for alias in connections:
    with connections[alias].cursor() as cursor:
        cursor.execute('SELECT 1')
        cursor.execute('SELECT COUNT(*) FROM licencas')
        cursor.execute('SELECT COUNT(*) FROM usuarios')
        cursor.execute('SELECT COUNT(*) FROM empresas')
        cursor.execute('SELECT COUNT(*) FROM filiais')
        cursor.execute('SELECT COUNT(*) FROM modulosmobile')
        cursor.execute('SELECT COUNT(*) FROM permissoesmodulosmobile')
print('✅ Pool de conexões 100% aquecido')

# 2. Cache MASSIVO de módulos
try:
    modulos = list(Modulo.objects.filter(modu_ativ=True).order_by('modu_orde'))
    cache.set('modulos_globais', modulos, 7200)  # 2 horas
    cache.set('modulos_count', len(modulos), 7200)
    print(f'✅ {len(modulos)} módulos em cache (2h)')
except Exception as e:
    print(f'⚠️ Erro módulos: {e}')

# 3. Cache AGRESSIVO de permissões por empresa/filial
try:
    empresas = Empresas.objects.all()
    total_cached = 0
    
    for empresa in empresas:
        # Cache empresa
        cache.set(f'empresa_{empresa.empr_codi}', empresa, 3600)
        
        filiais = Filiais.objects.filter(empr_codi=empresa.empr_codi)
        for filial in filiais:
            # Cache filial
            cache.set(f'filial_{filial.empr_empr}', filial, 3600)
            
            # Cache permissões com select_related
            perms = list(PermissaoModulo.objects.filter(
                perm_empr=empresa.empr_codi,
                perm_fili=filial.empr_empr,
                perm_ativ=True
            ).select_related('perm_modu'))
            
            cache_key = f'perms_{empresa.empr_codi}_{filial.empr_empr}'
            cache.set(cache_key, perms, 3600)
            
            # Cache módulos liberados (lista de IDs)
            modulos_ids = [p.perm_modu.modu_codi for p in perms]
            cache.set(f'modulos_liberados_{empresa.empr_codi}_{filial.empr_empr}', modulos_ids, 3600)
            
            total_cached += len(perms)
    
    print(f'✅ {total_cached} permissões em cache agressivo')
except Exception as e:
    print(f'⚠️ Erro permissões: {e}')

# 4. Cache de licenças com índice
try:
    licencas = list(Licencas.objects.filter(lice_bloq=False))
    cache.set('licencas_ativas', licencas, 3600)
    
    # Índice por CNPJ para busca rápida
    licencas_index = {lic.lice_docu: lic for lic in licencas}
    cache.set('licencas_index_cnpj', licencas_index, 3600)
    
    print(f'✅ {len(licencas)} licenças + índice em cache')
except Exception as e:
    print(f'⚠️ Erro licenças: {e}')

# 5. Simular 50 logins para aquecer TUDO
print('🔥 Simulando logins para aquecimento total...')
try:
    usuarios_sample = Usuarios.objects.all()[:10]
    empresas_sample = Empresas.objects.all()[:5]
    
    for user in usuarios_sample:
        for emp in empresas_sample:
            filiais_sample = Filiais.objects.filter(empr_codi=emp.empr_codi)[:3]
            for filial in filiais_sample:
                # Simular verificação de permissões
                PermissaoModulo.objects.filter(
                    perm_empr=emp.empr_codi,
                    perm_fili=filial.empr_empr,
                    perm_ativ=True
                ).exists()
                
                # Simular busca de módulos
                Modulo.objects.filter(
                    modu_ativ=True,
                    permissoes__perm_empr=emp.empr_codi,
                    permissoes__perm_fili=filial.empr_empr,
                    permissoes__perm_ativ=True
                ).exists()
    
    print('✅ Simulação de logins concluída')
except Exception as e:
    print(f'⚠️ Erro simulação: {e}')

# 6. Pré-compilar queries frequentes
try:
    # Forçar compilação de queries ORM
    list(Usuarios.objects.all()[:1])
    list(Empresas.objects.all()[:1])
    list(Filiais.objects.all()[:1])
    list(Modulo.objects.filter(modu_ativ=True)[:1])
    list(PermissaoModulo.objects.filter(perm_ativ=True)[:1])
    print('✅ Queries ORM pré-compiladas')
except Exception as e:
    print(f'⚠️ Erro compilação: {e}')

end_time = time.time()
print(f'🚀 PRÉ-AQUECIMENTO CONCLUÍDO em {end_time - start_time:.2f}s')
print('💡 Sistema pronto para LOGIN INSTANTÂNEO!')
"

# --- Aguardar estabilização total ---
echo "⏳ Aguardando estabilização total..."
sleep 3

# --- Iniciar Gunicorn com configuração ULTRA-OTIMIZADA ---
echo "🚀 Iniciando servidor ULTRA-OTIMIZADO..."
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class gevent \
    --worker-connections 2000 \
    --max-requests 2000 \
    --max-requests-jitter 200 \
    --preload \
    --timeout 180 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
