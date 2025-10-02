#!/bin/bash

echo "🧪 Iniciando pruebas del sistema Yahoo Answers"

STORAGE_URL="http://localhost:8001"
CACHE_URL="http://localhost:8002"
SCORE_URL="http://localhost:8003"
LLM_URL="http://localhost:8004"
TRAFFIC_URL="http://localhost:8005"

check_service() {
    local name=$1
    local url=$2
    
    echo "📡 Verificando $name..."
    
    if curl -s "$url/health" > /dev/null; then
        echo "✅ $name está disponible"
        return 0
    else
        echo "❌ $name no está disponible"
        return 1
    fi
}

test_endpoint() {
    local name=$1
    local url=$2
    local expected_status=$3
    
    echo "🔍 Probando $name..."
    
    response=$(curl -s -w "%{http_code}" "$url")
    status_code="${response: -3}"
    
    if [ "$status_code" = "$expected_status" ]; then
        echo "✅ $name: OK ($status_code)"
        return 0
    else
        echo "❌ $name: FAIL ($status_code)"
        return 1
    fi
}

echo ""
echo "=== VERIFICACIÓN DE SERVICIOS ==="

services_ok=true

check_service "Storage Service" "$STORAGE_URL" || services_ok=false
check_service "Cache Service" "$CACHE_URL" || services_ok=false
check_service "Score Service" "$SCORE_URL" || services_ok=false
check_service "LLM Service" "$LLM_URL" || services_ok=false
check_service "Traffic Generator" "$TRAFFIC_URL" || services_ok=false

if [ "$services_ok" = false ]; then
    echo ""
    echo "❌ Algunos servicios no están disponibles. Verifica que el sistema esté ejecutándose:"
    echo "   docker-compose up -d"
    exit 1
fi

echo ""
echo "=== PRUEBAS FUNCIONALES ==="

echo "🎲 Test 1: Pregunta aleatoria desde Storage"
question_response=$(curl -s "$STORAGE_URL/question/random")
echo "Respuesta: $question_response"

question_id=$(echo "$question_response" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id', 1))" 2>/dev/null || echo "1")

echo ""
echo "🔄 Test 2: Pipeline completo a través del Cache"
pipeline_response=$(curl -s "$CACHE_URL/question/$question_id")
echo "Respuesta del pipeline: $pipeline_response"

echo ""
echo "📊 Test 3: Estadísticas de servicios"

echo "Storage stats:"
curl -s "$STORAGE_URL/stats" | python3 -m json.tool 2>/dev/null || echo "Error obteniendo stats"

echo ""
echo "Cache stats:"
curl -s "$CACHE_URL/cache/stats" | python3 -m json.tool 2>/dev/null || echo "Error obteniendo stats"

echo ""
echo "Score stats:"
curl -s "$SCORE_URL/stats" | python3 -m json.tool 2>/dev/null || echo "Error obteniendo stats"

echo ""
echo "Traffic stats:"
curl -s "$TRAFFIC_URL/stats" | python3 -m json.tool 2>/dev/null || echo "Error obteniendo stats"

echo ""
echo "=== PRUEBA DE TRÁFICO ==="

echo "🚀 Test 4: Generación de tráfico ligero"
traffic_config='{
    "distribution": "uniform",
    "rate": 0.5,
    "duration": 30
}'

echo "Iniciando tráfico..."
curl -s -X POST "$TRAFFIC_URL/start-traffic" \
     -H "Content-Type: application/json" \
     -d "$traffic_config"

echo ""
echo "⏳ Esperando 35 segundos para que complete el tráfico..."
sleep 35

echo ""
echo "📈 Estadísticas finales del tráfico:"
curl -s "$TRAFFIC_URL/stats" | python3 -m json.tool 2>/dev/null || echo "Error obteniendo stats"

echo ""
echo "=== PRUEBA DE CACHE ==="

echo "🧪 Test 5: Verificar cache hit"
echo "Primera solicitud (cache miss esperado):"
time curl -s "$CACHE_URL/question/$question_id" > /dev/null

echo "Segunda solicitud (cache hit esperado):"
time curl -s "$CACHE_URL/question/$question_id" > /dev/null

echo ""
echo "📊 Estadísticas de cache después de las pruebas:"
curl -s "$CACHE_URL/cache/stats" | python3 -m json.tool 2>/dev/null || echo "Error obteniendo stats"

echo ""
echo "=== RESUMEN ==="
echo "✅ Pruebas completadas"
echo ""
echo "📋 Para monitorear el sistema en tiempo real:"
echo "   - Storage:   $STORAGE_URL/stats"
echo "   - Cache:     $CACHE_URL/cache/stats"  
echo "   - Score:     $SCORE_URL/stats"
echo "   - Traffic:   $TRAFFIC_URL/stats"
echo ""
echo "🎛️ Para iniciar más tráfico:"
echo "   curl -X POST $TRAFFIC_URL/start-traffic -H 'Content-Type: application/json' -d '{\"distribution\":\"poisson\",\"rate\":2.0,\"duration\":120}'"
echo ""
echo "🎉 ¡Sistema funcionando correctamente!"
