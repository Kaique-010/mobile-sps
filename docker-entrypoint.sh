#!/bin/bash
set -e

# Aguarda Redis estar disponível
echo "Aguardando Redis..."
while ! redis-cli -h redis ping > /dev/null 2>&1; do
  sleep 1
done
echo "Redis conectado!"

# Executa migrações
echo "Executando migrações..."
python manage.py migrate

# Coleta arquivos estáticos
echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

# Aquece o cache de permissões
echo "Aquecendo cache de permissões..."
python manage.py shell -c "
from django.core.cache import cache
from parametros_admin.models import PermissaoModulo
print('Pré-carregando permissões no cache...')
for perm in PermissaoModulo.objects.select_related('empresa', 'modulo').all():
    cache_key = f'permissoes_empresa_{perm.empresa.id}'
    cache.set(cache_key, True, 3600)
print('Cache aquecido!')
"

# Inicia o servidor
echo "Iniciando servidor..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
