# Usar imagen ligera de Python
FROM python:3.10-slim

# Evitar que Python genere archivos .pyc y buffer de salida
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema (necesario para psycopg2 a veces)
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el cÃ³digo
COPY . .

# Exponer puerto (Railway/Render inyectan PORT, pero bueno saberlo)
EXPOSE 8000

# Comando de ejecuciÃ³n (Usa PORT de entorno, default 8000)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
