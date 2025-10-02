#!/bin/bash

echo "🔍 VERIFICACIÓN RÁPIDA DE SERVICIOS"
echo "=================================="

check_url() {
    local service=$1
    local url=$2
    echo -n "📡 $service: "
    
    if curl -s --max-time 5 "$url" > /dev/null 2>&1; then
        echo "✅ OK"
        return 0
    else
        echo "❌ No disponible"
        return 1
    fi
}

check_json() {
    local service=$1 
    local url=$2
    echo "📊 $service:"
    
    response=$(curl -s --max-time 5 "$url" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
        echo ""
        return 0
    else
        echo "❌ No disponible o error en respuesta"
        echo ""
        return 1
    fi
}

echo ""
echo "=== HEALTH CHECKS ==="
check_url "Storage Service" "http://localhost:8001/health"
check_url "Cache Service" "http://localhost:8002/health"  
check_url "Score Service" "http://localhost:8003/health"
check_url "LLM Service" "http://localhost:8004/health"
check_url "Traffic Generator" "http://localhost:8005/health"

echo ""
echo "=== ESTADÍSTICAS BÁSICAS ==="
check_json "Storage Stats" "http://localhost:8001/stats"
check_json "Cache Stats" "http://localhost:8002/cache/stats"
check_json "Traffic Stats" "http://localhost:8005/stats"

echo ""
echo "=== PRUEBA BÁSICA DEL PIPELINE ==="
echo "🎯 Obteniendo pregunta aleatoria..."
question_response=$(curl -s --max-time 10 "http://localhost:8001/question/random" 2>/dev/null)

if [ $? -eq 0 ] && [ -n "$question_response" ]; then
    echo "✅ Storage responde:"
    echo "$question_response" | python3 -m json.tool 2>/dev/null || echo "$question_response"
    
    question_id=$(echo "$question_response" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id', 1))" 2>/dev/null || echo "1")
    
    echo ""
    echo "🔄 Probando pipeline completo con pregunta ID: $question_id"
    pipeline_response=$(curl -s --max-time 30 "http://localhost:8002/question/$question_id" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$pipeline_response" ]; then
        echo "✅ Pipeline funciona:"
        echo "$pipeline_response" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(f'Question ID: {data.get(\"question_id\", \"N/A\")}')
    print(f'Cache Hit: {data.get(\"cache_hit\", \"N/A\")}')
    print(f'Response Time: {data.get(\"response_time_ms\", \"N/A\")}ms')
    if 'llm_response' in data:
        print(f'LLM Response: {data[\"llm_response\"][:100]}...')
    if 'composite_score' in data:
        print(f'Quality Score: {data[\"composite_score\"]}')
except:
    print('Raw response:', file=sys.stderr)
    sys.stdin.seek(0)
    print(sys.stdin.read())
" 2>/dev/null
    else
        echo "❌ Pipeline no responde correctamente"
    fi
else
    echo "❌ Storage no responde"
fi

echo ""
echo "=== RESUMEN ==="
echo "✅ Ejecutar para monitoreo continuo: watch -n 5 './quick_check.sh'"
echo "✅ Ejecutar para pruebas completas: './test_system.sh'"
echo "✅ Ver logs: docker-compose logs -f"
