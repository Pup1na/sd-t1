#!/bin/bash

# Script para mostrar estadísticas de cache en tiempo real durante la ejecución
echo "📊 MONITOR DE CACHE HITS EN TIEMPO REAL"
echo "======================================"
echo "Ejecuta este script en una terminal separada mientras el sistema está funcionando"
echo ""

# Contadores
total_hits=0
total_misses=0
last_hits=0
last_misses=0

while true; do
    # Obtener estadísticas del cache
    cache_stats=$(curl -s http://localhost:8002/cache/stats 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$cache_stats" ]; then
        # Extraer métricas usando python
        current_keys=$(echo "$cache_stats" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('total_keys', 0))
except:
    print('0')
" 2>/dev/null)
        
        # Obtener estadísticas de storage para cache hits
        storage_stats=$(curl -s http://localhost:8001/stats 2>/dev/null)
        if [ $? -eq 0 ] && [ -n "$storage_stats" ]; then
            cache_info=$(echo "$storage_stats" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    hits = data.get('total_cache_hits', 0) or 0
    accesses = data.get('total_accesses', 0) or 0
    misses = accesses - hits
    hit_rate = (hits / accesses * 100) if accesses > 0 else 0
    print(f'{hits},{misses},{hit_rate:.1f}')
except:
    print('0,0,0.0')
" 2>/dev/null)
            
            IFS=',' read -r hits misses hit_rate <<< "$cache_info"
            
            # Calcular incrementos desde la última medición
            hit_increment=$((hits - last_hits))
            miss_increment=$((misses - last_misses))
            
            # Actualizar contadores
            last_hits=$hits
            last_misses=$misses
            
            # Mostrar estadísticas
            clear
            echo "📊 ESTADÍSTICAS DE CACHE EN TIEMPO REAL"
            echo "========================================"
            echo "🕐 $(date '+%H:%M:%S')"
            echo ""
            echo "📈 RESUMEN TOTAL:"
            echo "   🎯 Cache Hits: $hits"
            echo "   💾 Cache Misses: $misses"  
            echo "   📊 Hit Rate: $hit_rate%"
            echo "   🔑 Keys en cache: $current_keys"
            echo ""
            echo "⚡ ACTIVIDAD RECIENTE (últimos 5s):"
            if [ $hit_increment -gt 0 ]; then
                echo "   ✅ +$hit_increment cache hits"
            fi
            if [ $miss_increment -gt 0 ]; then
                echo "   💾 +$miss_increment cache misses"
            fi
            if [ $hit_increment -eq 0 ] && [ $miss_increment -eq 0 ]; then
                echo "   💤 Sin actividad"
            fi
            echo ""
            echo "🎛️  CONFIGURACIÓN ACTUAL:"
            cache_config=$(echo "$cache_stats" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(f\"Policy: {data.get('policy', 'N/A')}, TTL: {data.get('ttl', 'N/A')}s, Max: {data.get('max_size', 'N/A')}\")
except:
    print('No disponible')
" 2>/dev/null)
            echo "   $cache_config"
            echo ""
            echo "💡 Para detener: Ctrl+C"
        else
            echo "⚠️  Storage service no disponible"
        fi
    else
        echo "❌ Cache service no disponible"
        echo "   Verifica que el sistema esté ejecutándose: docker-compose up"
    fi
    
    sleep 5
done
