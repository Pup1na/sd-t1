# Comandos Útiles para el Proyecto

## 🚀 Comandos de Desarrollo

### Configuración Inicial
```bash
# Copiar variables de entorno
cp .env.example .env

# Editar .env con tu API key
nano .env
```

### Gestión de Datos
```bash
# Descargar dataset de Kaggle
./download_data.sh

# Levantar solo la base de datos
docker-compose up -d postgres

# Cargar datos a la base de datos
docker-compose --profile tools run --rm data_loader

# Ver logs de la carga
docker-compose logs data_loader
```

### Gestión de Servicios
```bash
# Levantar todo el sistema
docker-compose up --build

# Levantar en background
docker-compose up -d --build

# Ver logs de un servicio específico
docker-compose logs -f storage
docker-compose logs -f cache

# Rebuild un servicio específico
docker-compose up --build storage

# Parar todo
docker-compose down

# Parar y limpiar volúmenes
docker-compose down -v
```

### Testing y Debug
```bash
# Conectar a PostgreSQL directamente
docker-compose exec postgres psql -U admin -d yahoo_answers

# Ver estadísticas de la base de datos
curl http://localhost:8001/stats

# Obtener pregunta aleatoria
curl http://localhost:8001/question/random

# Health check de servicios
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### Consultas SQL Útiles
```sql
-- Ver total de preguntas
SELECT COUNT(*) FROM yahoo_questions;

-- Ver preguntas por clase
SELECT class_id, COUNT(*) FROM yahoo_questions GROUP BY class_id;

-- Ver estadísticas de acceso
SELECT 
    yq.title,
    qs.access_count,
    qs.cache_hits,
    qs.last_accessed
FROM yahoo_questions yq
JOIN question_stats qs ON yq.id = qs.question_id
ORDER BY qs.access_count DESC
LIMIT 10;

-- Ver respuestas del LLM
SELECT 
    yq.title,
    lr.llm_response,
    lr.quality_score,
    lr.created_at
FROM llm_responses lr
JOIN yahoo_questions yq ON lr.question_id = yq.id
ORDER BY lr.created_at DESC
LIMIT 5;
```

### Limpieza
```bash
# Limpiar contenedores parados
docker container prune

# Limpiar imágenes no usadas
docker image prune

# Limpiar todo (cuidado!)
docker system prune -a

# Resetear volúmenes de datos
docker-compose down -v
docker volume rm $(docker volume ls -q | grep tarea-1)
```

### Monitoreo
```bash
# Ver uso de recursos
docker stats

# Ver logs en tiempo real
docker-compose logs -f

# Ver solo errores
docker-compose logs | grep -i error
```
