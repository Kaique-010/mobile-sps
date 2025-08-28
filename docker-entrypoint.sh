#!/bin/bash
set -e

# --- Aguardar Redis estar disponível ---
echo "Aguardando Redis..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis disponível!"

# --- Executar migrações ---
echo "Executando migrações..."
python manage.py migrate --noinput

# --- PRÉ-AQUECIMENTO DO POOL DE CONEXÕES ---
echo "Pré-aquecendo pool de conexões do banco..."
python manage.py shell -c "
import django
import time
from django.db import connection
from django.core.cache import cache
from Licencas.models import Licencas, Usuarios, Empresas, Filiais
from parametros_admin.models import Modulo, PermissaoModulo

print('=== INICIANDO PRÉ-AQUECIMENTO MULTI-EMPRESA/FILIAL ===')
start_time = time.time()

# 1. Aquecer conexões básicas
with connection.cursor() as cursor:
    cursor.execute('SELECT 1')
    cursor.execute('SELECT COUNT(*) FROM licencas')
    cursor.execute('SELECT COUNT(*) FROM usuarios')
    cursor.execute('SELECT COUNT(*) FROM empresas')
    cursor.execute('SELECT COUNT(*) FROM filiais')
    cursor.execute('SELECT COUNT(*) FROM parametros_admin_modulo')
    cursor.execute('SELECT COUNT(*) FROM parametros_admin_permissaomodulo')
print('✓ Conexões básicas aquecidas')

# 2. Pré-carregar módulos globais no cache
try:
    modulos = list(Modulo.objects.all()[:50])
    cache.set('modulos_globais', modulos, 3600)
    print(f'✓ {len(modulos)} módulos globais carregados no cache')
except Exception as e:
    print(f'Aviso: Erro ao cachear módulos globais: {e}')

# 3. Pré-carregar empresas, filiais e permissões no cache
try:
    empresas = Empresas.objects.all()
    total_perms = 0
    for empresa in empresas:
        filiais = Filiais.objects.filter(empr_empr=empresa.id)
        for filial in filiais:
            perms = PermissaoModulo.objects.filter(
                empresa_id=empresa.id,
                filial_id=filial.id
            ).select_related('modulo')
            cache_key = f'perms_empresa_{empresa.id}_filial_{filial.id}'
            cache.set(cache_key, list(perms), 3600)
            total_perms += len(perms)
    print(f'✓ Permissões pré-carregadas: {total_perms} itens (multi-empresa/filial)')
except Exception as e:
    print(f'Aviso: Erro ao pré-carregar permissões: {e}')

# 4. Testar queries típicas de login para todos os usuários ativos
try:
    test_users = Usuarios.objects.filter(ativo=True)
    for user in test_users:
        empresas_user = Empresas.objects.filter(usuario_id=user.id)
        for emp in empresas_user:
            filiais_user = Filiais.objects.filter(empr_empr=emp.id)
            for filial in filiais_user:
                PermissaoModulo.objects.filter(
                    empresa_id=emp.id,
                    filial_id=filial.id
                ).exists()
    print('✓ Queries de login multi-empresa/filial testadas')
except Exception as e:
    print(f'Aviso: Erro ao testar queries de login: {e}')

end_time = time.time()
print(f'=== PRÉ-AQUECIMENTO CONCLUÍDO em {end_time - start_time:.2f}s ===')
"

# --- Pequena pausa para estabilização ---
echo "Aguardando estabilização..."
sleep 2

# --- Iniciar servidor Django com Gunicorn ---
echo "Iniciando servidor Django com pool aquecido..."
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload \
    --timeout 120
