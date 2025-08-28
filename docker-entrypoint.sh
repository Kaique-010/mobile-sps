#!/bin/bash
set -e

# Aguardar Redis estar disponível
echo "Aguardando Redis..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis disponível!"

# Executar migrações
echo "Executando migrações..."
python manage.py migrate --noinput

# Coletar arquivos estáticos
echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

# Aquecer cache de permissões
echo "Aquecendo cache de permissões..."
python manage.py shell -c "
from django.core.cache import cache
from parametros_admin.utils import get_modulos_liberados_empresa
from Licencas.models import Empresas
print('Aquecendo cache...')
for empresa in Empresas.objects.all()[:10]:  # Primeiras 10 empresas
    try:
        get_modulos_liberados_empresa(empresa.id, empresa.filial_id)
        print(f'Cache aquecido para empresa {empresa.id}')
    except:
        pass
print('Cache aquecido!')
"

# Iniciar servidor
echo "Iniciando servidor Django..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
