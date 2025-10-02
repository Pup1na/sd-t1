FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY loader.py .
COPY entrypoint.sh .

# Hacer ejecutable el entrypoint
RUN chmod +x entrypoint.sh

# Comando por defecto
ENTRYPOINT ["./entrypoint.sh"]
