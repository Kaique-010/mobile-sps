#!/bin/bash
echo "🚀 BUILD TURBO MODE!"

# Habilitar BuildKit
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Build com cache agressivo
docker-compose build \
    --parallel \
    --compress \
    --force-rm \
    --pull

# Up com otimizações
docker-compose up -d \
    --remove-orphans \
    --force-recreate

echo "✅ Build concluído!"