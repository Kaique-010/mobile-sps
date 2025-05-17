FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências básicas do sistema
RUN apt-get update \
    && apt-get install -y gcc libpq-dev build-essential \
    && apt-get clean

# Copia e instala dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia o restante da aplicação
COPY . .

# Comando para subir o app
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
