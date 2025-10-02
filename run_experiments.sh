#!/bin/bash
"""
Script para ejecutar experimentos de cache con diferentes configuraciones
"""

# Función para ejecutar experimento con configuración específica
run_experiment() {
    local cache_size=$1
    local cache_policy=$2
    local cache_ttl=$3
    local experiment_name=$4
    
    echo "🧪 Ejecutando experimento: $experiment_name"
    echo "   Cache Size: $cache_size, Policy: $cache_policy, TTL: $cache_ttl"
    
    # Detener cache service
    CACHE_MAX_SIZE=$cache_size CACHE_POLICY=$cache_policy CACHE_TTL=$cache_ttl docker-compose stop cache
    
    # Limpiar Redis
    docker-compose exec redis redis-cli FLUSHALL
    
    # Reiniciar cache con nueva configuración
    CACHE_MAX_SIZE=$cache_size CACHE_POLICY=$cache_policy CACHE_TTL=$cache_ttl docker-compose up -d cache
    
    # Esperar que se estabilice
    sleep 15
    
    # Resetear estadísticas
    curl -X POST http://localhost:8002/cache/reset-stats
    
    echo "✅ Experimento $experiment_name configurado"
}

# Función para ejecutar tráfico
run_traffic() {
    local distribution=$1
    local rate=$2
    local duration=$3
    
    echo "🚀 Generando tráfico: $distribution, rate=$rate, duration=${duration}s"
    
    curl -X POST http://localhost:8005/start-traffic -H 'Content-Type: application/json' \
         -d "{\"distribution\":\"$distribution\",\"rate\":$rate,\"duration\":$duration}"
    
    # Esperar que termine + margen
    sleep $((duration + 10))
}

# Función para capturar estadísticas
capture_stats() {
    local experiment_name=$1
    local results_dir="analysis_results"
    
    mkdir -p $results_dir
    
    echo "📊 Capturando estadísticas para: $experiment_name"
    
    # Estadísticas de cache
    curl -s http://localhost:8002/cache/stats > "${results_dir}/${experiment_name}_cache_stats.json"
    
    # Estadísticas de tráfico
    curl -s http://localhost:8005/stats > "${results_dir}/${experiment_name}_traffic_stats.json"
    
    # Keys en Redis
    docker-compose exec redis redis-cli DBSIZE > "${results_dir}/${experiment_name}_redis_size.txt"
}

echo "🔬 INICIANDO EXPERIMENTOS DE ANÁLISIS DE CACHE"
echo "=============================================="

cd "/Users/sebastianzuniga/Documents/Sistemas Distribuidos/Tarea-1-Sistemas-distribuidos"

# Asegurar que los servicios estén corriendo
docker-compose up -d

# Experimento 1: Cache pequeño LRU
run_experiment 10 "lru" 300 "small_lru"
run_traffic "uniform" 5.0 60
capture_stats "exp1_small_lru_uniform"

# Experimento 2: Cache pequeño LFU  
run_experiment 10 "lfu" 300 "small_lfu"
run_traffic "uniform" 5.0 60
capture_stats "exp2_small_lfu_uniform"

# Experimento 3: Cache pequeño FIFO
run_experiment 10 "fifo" 300 "small_fifo"
run_traffic "uniform" 5.0 60
capture_stats "exp3_small_fifo_uniform"

# Experimento 4: Cache mediano LRU - Poisson
run_experiment 50 "lru" 600 "medium_lru"
run_traffic "poisson" 4.0 60
capture_stats "exp4_medium_lru_poisson"

# Experimento 5: Cache grande LRU - Exponential
run_experiment 100 "lru" 1200 "large_lru"
run_traffic "exponential" 3.0 60
capture_stats "exp5_large_lru_exponential"

# Experimento 6: Cache pequeño - Alta carga
run_experiment 10 "lru" 180 "small_stress"
run_traffic "uniform" 10.0 45
capture_stats "exp6_small_stress_high_load"

echo "🎉 Todos los experimentos completados!"
echo "📋 Resultados guardados en: analysis_results/"
