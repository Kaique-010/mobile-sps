#!/bin/bash
set -e

# Função para log com timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "🚀 Iniciando container ULTRA-OTIMIZADO..."

# Aguardar Redis (máximo 10s)
log "⏳ Aguardando Redis..."
for i in {1..10}; do
    if nc -z redis 6379; then
        log "✅ Redis conectado!"
        break
    fi
    sleep 1
done

# Pré-aquecimento PARALELO
log "🔥 Iniciando pré-aquecimento paralelo..."
(
    # Coletar arquivos estáticos em background
    python manage.py collectstatic --noinput --clear &
    
    # Aquecer cache em background
    python -c "
    import django
    django.setup()
    from django.core.cache import cache
    cache.set('warmup', 'ready', 3600)
    print('✅ Cache aquecido')
    " &
    
    wait
) &

# Aguardar pré-aquecimento
wait

log "🚀 Iniciando Gunicorn OTIMIZADO..."
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-2} \
    --threads ${GUNICORN_THREADS:-4} \
    --worker-class gevent \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload \
    --timeout 120 \
    --keep-alive 300 \
    --log-level info
