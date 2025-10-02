#!/bin/bash

echo "🔄 Esperando que PostgreSQL esté listo..."

until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
    echo "⏳ PostgreSQL no está listo - esperando..."
    sleep 2
done

echo "✅ PostgreSQL está listo!"
echo "🚀 Iniciando carga de datos..."

python loader.py
