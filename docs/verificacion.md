# Guía de Verificación del Sistema - Paso a Paso

## 🚀 1. CONFIGURACIÓN INICIAL

### Configurar variables de entorno
```bash
cd "/Users/sebastianzuniga/Documents/Sistemas Distribuidos/Tarea-1-Sistemas-distribuidos"
cp .env.example .env

# Editar .env y agregar tu GEMINI_API_KEY
nano .env
# o
code .env
```

### Verificar configuración
```bash
# Ver si las variables están configuradas
cat .env
```

## 🗄️ 2. VERIFICAR BASE DE DATOS

### Levantar PostgreSQL
```bash
docker-compose up -d postgres
```

### Verificar PostgreSQL
```bash
# Ver logs de PostgreSQL
docker-compose logs postgres

# Conectar directamente a la BD
docker-compose exec postgres psql -U admin -d yahoo_answers -c "SELECT version();"
```

## 📊 3. CARGAR DATOS

### Ejecutar Data Loader
```bash
docker-compose --profile tools run --rm data_loader
```

### Verificar carga de datos
```bash
# Ver logs del data loader
docker-compose logs data_loader

# Verificar datos en BD
docker-compose exec postgres psql -U admin -d yahoo_answers -c "SELECT COUNT(*) FROM yahoo_questions;"
docker-compose exec postgres psql -U admin -d yahoo_answers -c "SELECT title FROM yahoo_questions LIMIT 3;"
```

## 🐳 4. LEVANTAR TODOS LOS SERVICIOS

### Iniciar sistema completo
```bash
docker-compose up --build
```

### Ver logs en tiempo real
```bash
# Logs de todos los servicios
docker-compose logs -f

# Logs de un servicio específico
docker-compose logs -f storage
docker-compose logs -f cache
docker-compose logs -f llm_service
docker-compose logs -f score_service
docker-compose logs -f traffic_generator
```

## 🔍 5. VERIFICAR CADA SERVICIO

### A. Storage Service (Puerto 8001)
```bash
# Health check
curl http://localhost:8001/health

# Obtener estadísticas
curl http://localhost:8001/stats | python3 -m json.tool

# Obtener pregunta aleatoria
curl http://localhost:8001/question/random | python3 -m json.tool

# Obtener pregunta específica
curl http://localhost:8001/question/1 | python3 -m json.tool
```

### B. Cache Service (Puerto 8002)
```bash
# Health check
curl http://localhost:8002/health

# Ver estadísticas del cache
curl http://localhost:8002/cache/stats | python3 -m json.tool

# Probar consulta (debe pasar por todo el pipeline)
curl http://localhost:8002/question/1 | python3 -m json.tool

# Segunda consulta (debería ser cache hit)
curl http://localhost:8002/question/1 | python3 -m json.tool
```

### C. Score Service (Puerto 8003)
```bash
# Health check
curl http://localhost:8003/health

# Ver estadísticas
curl http://localhost:8003/stats | python3 -m json.tool

# Probar evaluación de score
curl -X POST http://localhost:8003/test-score \
  -H "Content-Type: application/json" \
  -d '{"text1":"This is AI","text2":"Artificial intelligence is technology"}' | python3 -m json.tool
```

### D. LLM Service (Puerto 8004)
```bash
# Health check
curl http://localhost:8004/health

# Ver información del modelo
curl http://localhost:8004/model-info | python3 -m json.tool

# Probar generación (requiere GEMINI_API_KEY configurada)
curl -X POST http://localhost:8004/test-generation \
  -H "Content-Type: application/json" \
  -d '{"question":"What is machine learning?"}' | python3 -m json.tool
```

### E. Traffic Generator (Puerto 8005)
```bash
# Health check
curl http://localhost:8005/health

# Ver estadísticas
curl http://localhost:8005/stats | python3 -m json.tool

# Ver patrones disponibles
curl http://localhost:8005/patterns | python3 -m json.tool

# Probar solicitud individual
curl -X POST http://localhost:8005/test-request | python3 -m json.tool
```

## 🧪 6. PRUEBAS DEL PIPELINE COMPLETO

### Ejecutar script de pruebas automático
```bash
./test_system.sh
```

### Pruebas manuales paso a paso
```bash
# 1. Obtener una pregunta
QUESTION_ID=$(curl -s http://localhost:8001/question/random | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
echo "Testing with question ID: $QUESTION_ID"

# 2. Primera consulta (cache miss esperado)
echo "=== Primera consulta (cache miss) ==="
time curl -s http://localhost:8002/question/$QUESTION_ID | python3 -m json.tool

# 3. Segunda consulta (cache hit esperado)  
echo "=== Segunda consulta (cache hit) ==="
time curl -s http://localhost:8002/question/$QUESTION_ID | python3 -m json.tool

# 4. Ver estadísticas actualizadas
echo "=== Estadísticas de cache ==="
curl -s http://localhost:8002/cache/stats | python3 -m json.tool
```

## 🚦 7. GENERAR TRÁFICO SINTÉTICO

### Tráfico ligero de prueba
```bash
curl -X POST http://localhost:8005/start-traffic \
  -H "Content-Type: application/json" \
  -d '{
    "distribution": "uniform",
    "rate": 0.5,
    "duration": 30
  }'

# Monitorear progreso
watch -n 2 "curl -s http://localhost:8005/stats | python3 -m json.tool"
```

### Tráfico normal
```bash
curl -X POST http://localhost:8005/start-traffic \
  -H "Content-Type: application/json" \
  -d '{
    "distribution": "poisson", 
    "rate": 2.0,
    "duration": 120
  }'
```

## 📊 8. MONITOREO CONTINUO

### Dashboard de estadísticas
```bash
# Script para monitorear todos los servicios
while true; do
  clear
  echo "=== SYSTEM STATUS $(date) ==="
  echo ""
  echo "Storage Stats:"
  curl -s http://localhost:8001/stats 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Service unavailable"
  echo ""
  echo "Cache Stats:"
  curl -s http://localhost:8002/cache/stats 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Service unavailable"  
  echo ""
  echo "Traffic Stats:"
  curl -s http://localhost:8005/stats 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Service unavailable"
  echo ""
  sleep 5
done
```

### Ver logs en tiempo real
```bash
# Terminal 1: Logs generales
docker-compose logs -f

# Terminal 2: Estadísticas específicas
watch -n 3 "echo 'Cache:'; curl -s http://localhost:8002/cache/stats | python3 -m json.tool"

# Terminal 3: Monitoreo de sistema
docker stats
```

## 🔧 9. TROUBLESHOOTING

### Verificar contenedores
```bash
# Ver estado de contenedores
docker-compose ps

# Ver uso de recursos
docker stats

# Reiniciar servicio específico
docker-compose restart cache
docker-compose restart llm_service
```

### Verificar conectividad entre servicios
```bash
# Desde el contenedor de cache, probar conexión a storage
docker-compose exec cache curl http://storage:8000/health

# Desde traffic_generator, probar conexión a cache
docker-compose exec traffic_generator curl http://cache:8000/health
```

### Ver logs de errores
```bash
# Filtrar solo errores
docker-compose logs | grep -i error

# Logs específicos con timestamp
docker-compose logs -t cache | tail -50
```

## ✅ 10. CHECKLIST DE VERIFICACIÓN

- [ ] PostgreSQL conecta y tiene datos
- [ ] Redis funciona para cache  
- [ ] Storage API responde correctamente
- [ ] Cache intercepta y almacena consultas
- [ ] LLM Service genera respuestas (requiere API key)
- [ ] Score Service evalúa calidad
- [ ] Traffic Generator puede simular carga
- [ ] Pipeline completo funciona end-to-end
- [ ] Métricas se recolectan correctamente
- [ ] Sistema maneja errores gracefully
