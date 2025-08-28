#!/bin/bash
echo "🚀 BUILD TURBO MODE!"

# Desabilitar BuildKit temporariamente
export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0

# Verificar se Docker está rodando
if ! sudo docker info > /dev/null 2>&1; then
    echo "❌ Docker não está rodando. Iniciando..."
    sudo systemctl start docker
    sleep 2
fi

# Build sem BuildKit
echo "📦 Building sem BuildKit..."
sudo docker-compose build backend

# Up dos serviços
echo "🔥 Subindo serviços..."
sudo docker-compose up -d

# Aguardar health check
echo "⏳ Aguardando health check..."
for i in {1..30}; do
    if sudo docker-compose ps | grep -q "healthy\|Up"; then
        echo "✅ Serviços prontos em ${i}s!"
        break
    fi
    sleep 1
done

echo "🎉 BUILD TURBO CONCLUÍDO!"
sudo docker-compose ps