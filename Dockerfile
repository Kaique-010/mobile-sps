FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências do sistema + Redis tools
RUN apt-get update \
    && apt-get install -y gcc libpq-dev build-essential redis-tools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Instala dependências para cache e Celery
RUN pip install redis django-redis celery[redis]

# Copia o restante da aplicação
COPY . .

# Script de inicialização
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Comando padrão
CMD ["/docker-entrypoint.sh"]
