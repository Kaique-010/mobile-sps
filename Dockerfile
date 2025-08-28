# Stage 1: Build dependencies
FROM python:3.11-slim-bookworm AS builder
WORKDIR /build

# Instalar dependências de build
RUN apk add --no-cache gcc musl-dev postgresql-dev libffi-dev

# Copiar e instalar requirements
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime MÍNIMO
FROM python:3.11-slim-bookworm
WORKDIR /app

# Instalar apenas runtime essencial
RUN apk add --no-cache postgresql-client curl \
    && addgroup -g 1000 appuser \
    && adduser -D -u 1000 -G appuser appuser

# Copiar dependências do builder
COPY --from=builder /root/.local /home/appuser/.local

# Copiar docker-entrypoint.sh ANTES de mudar usuário
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copiar código
COPY --chown=appuser:appuser . .

# Configurar PATH e usuário
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser
EXPOSE 8000

# Health check otimizado
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=2 \
    CMD curl -f http://localhost:8000/health/ || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]