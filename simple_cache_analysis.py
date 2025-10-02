#!/usr/bin/env python3
"""
Script simplificado para análisis rápido de cache
"""

import time
import json
import requests
import subprocess
import pandas as pd
import matplotlib.pyplot as plt

def run_cache_experiment(cache_size=10, policy='lru', ttl=300, traffic_rate=5.0, traffic_duration=60, distribution='uniform'):
    """Ejecutar un experimento simple de cache"""
    
    print(f"🧪 Experimento: Cache({cache_size}, {policy}, {ttl}s) + Traffic({distribution}, {traffic_rate}req/s, {traffic_duration}s)")
    
    # 1. Configurar variables de entorno y reiniciar cache
    subprocess.run([
        "docker-compose", "stop", "cache"
    ], cwd="/Users/sebastianzuniga/Documents/Sistemas Distribuidos/Tarea-1-Sistemas-distribuidos")
    
    # Limpiar Redis
    subprocess.run([
        "docker-compose", "exec", "-T", "redis", "redis-cli", "FLUSHALL"
    ], cwd="/Users/sebastianzuniga/Documents/Sistemas Distribuidos/Tarea-1-Sistemas-distribuidos")
    
    # Reiniciar con variables de entorno
    env = {
        'CACHE_MAX_SIZE': str(cache_size),
        'CACHE_POLICY': policy,
        'CACHE_TTL': str(ttl)
    }
    
    subprocess.run([
        "docker-compose", "up", "-d", "cache"
    ], cwd="/Users/sebastianzuniga/Documents/Sistemas Distribuidos/Tarea-1-Sistemas-distribuidos")
    
    time.sleep(10)  # Esperar que se inicialice
    
    # 2. Obtener estado inicial
    initial_redis_size = get_redis_size()
    print(f"📊 Estado inicial: Redis size = {initial_redis_size}")
    
    # 3. Generar tráfico
    print(f"🚀 Iniciando tráfico...")
    traffic_config = {
        "distribution": distribution,
        "rate": traffic_rate,
        "duration": traffic_duration
    }
    
    response = requests.post(
        "http://localhost:8005/start-traffic",
        json=traffic_config,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code != 200:
        print(f"❌ Error iniciando tráfico: {response.text}")
        return None
    
    # 4. Monitorear durante la ejecución
    timeline_data = []
    start_time = time.time()
    
    while True:
        # Verificar si el tráfico sigue corriendo
        traffic_stats = requests.get("http://localhost:8005/stats").json()
        if not traffic_stats.get('is_running', False):
            break
            
        # Capturar métricas actuales
        current_time = time.time() - start_time
        redis_size = get_redis_size()
        
        timeline_data.append({
            'time': current_time,
            'redis_size': redis_size,
            'total_requests': traffic_stats.get('total_requests', 0),
            'successful_requests': traffic_stats.get('successful_requests', 0)
        })
        
        print(f"⏱️  t={current_time:.1f}s: Redis={redis_size}, Requests={traffic_stats.get('total_requests', 0)}")
        time.sleep(3)
    
    # 5. Obtener estadísticas finales
    final_redis_size = get_redis_size()
    final_traffic = requests.get("http://localhost:8005/stats").json()
    
    total_requests = final_traffic.get('total_requests', 0)
    successful_requests = final_traffic.get('successful_requests', 0)
    
    # Estimar hits/misses basado en el comportamiento
    # Si el cache se llenó más allá de su tamaño, hubo evictions
    # Si hay menos elementos que requests únicos, hubo hits
    unique_questions = min(final_redis_size, 110)  # Máximo 110 preguntas en DB
    estimated_misses = min(unique_questions, cache_size)
    estimated_hits = max(0, total_requests - estimated_misses)
    
    hit_rate = estimated_hits / total_requests if total_requests > 0 else 0
    miss_rate = estimated_misses / total_requests if total_requests > 0 else 0
    
    result = {
        'config': {
            'cache_size': cache_size,
            'policy': policy,
            'ttl': ttl,
            'traffic_rate': traffic_rate,
            'traffic_duration': traffic_duration,
            'distribution': distribution
        },
        'metrics': {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'final_redis_size': final_redis_size,
            'estimated_hits': estimated_hits,
            'estimated_misses': estimated_misses,
            'hit_rate': hit_rate,
            'miss_rate': miss_rate,
            'cache_utilization': final_redis_size / cache_size if cache_size > 0 else 0,
            'throughput': successful_requests / traffic_duration,
            'success_rate': final_traffic.get('success_rate', 0)
        },
        'timeline': timeline_data
    }
    
    print(f"✅ Resultados: Hit Rate={hit_rate:.2%}, Throughput={result['metrics']['throughput']:.2f}req/s")
    return result

def get_redis_size():
    """Obtener número de keys en Redis"""
    try:
        result = subprocess.run([
            "docker-compose", "exec", "-T", "redis", "redis-cli", "DBSIZE"
        ], cwd="/Users/sebastianzuniga/Documents/Sistemas Distribuidos/Tarea-1-Sistemas-distribuidos",
        capture_output=True, text=True)
        
        return int(result.stdout.strip())
    except:
        return 0

def run_comprehensive_analysis():
    """Ejecutar múltiples experimentos para análisis completo"""
    
    experiments = [
        # Análisis por tamaño de cache
        {'cache_size': 5, 'policy': 'lru', 'ttl': 300, 'distribution': 'uniform', 'rate': 4.0, 'duration': 60},
        {'cache_size': 25, 'policy': 'lru', 'ttl': 300, 'distribution': 'uniform', 'rate': 4.0, 'duration': 60},
        {'cache_size': 50, 'policy': 'lru', 'ttl': 300, 'distribution': 'uniform', 'rate': 4.0, 'duration': 60},
        
        # Análisis por política
        {'cache_size': 15, 'policy': 'lru', 'ttl': 300, 'distribution': 'uniform', 'rate': 4.0, 'duration': 60},
        {'cache_size': 15, 'policy': 'lfu', 'ttl': 300, 'distribution': 'uniform', 'rate': 4.0, 'duration': 60},
        {'cache_size': 15, 'policy': 'fifo', 'ttl': 300, 'distribution': 'uniform', 'rate': 4.0, 'duration': 60},
        
        # Análisis por distribución de tráfico
        {'cache_size': 20, 'policy': 'lru', 'ttl': 300, 'distribution': 'uniform', 'rate': 4.0, 'duration': 60},
        {'cache_size': 20, 'policy': 'lru', 'ttl': 300, 'distribution': 'poisson', 'rate': 4.0, 'duration': 60},
        {'cache_size': 20, 'policy': 'lru', 'ttl': 300, 'distribution': 'exponential', 'rate': 4.0, 'duration': 60},
        {'cache_size': 20, 'policy': 'lru', 'ttl': 300, 'distribution': 'normal', 'rate': 4.0, 'duration': 60},
        
        # Análisis de stress (alta carga)
        {'cache_size': 10, 'policy': 'lru', 'ttl': 180, 'distribution': 'uniform', 'rate': 8.0, 'duration': 45},
    ]
    
    results = []
    
    print("🔬 INICIANDO ANÁLISIS EXPERIMENTAL COMPLETO")
    print("=" * 60)
    
    for i, exp_config in enumerate(experiments, 1):
        print(f"\n🧪 EXPERIMENTO {i}/{len(experiments)}")
        
        result = run_cache_experiment(
            cache_size=exp_config['cache_size'],
            policy=exp_config['policy'],
            ttl=exp_config['ttl'],
            distribution=exp_config['distribution'],
            traffic_rate=exp_config['rate'],
            traffic_duration=exp_config['duration']
        )
        
        if result:
            result['experiment_id'] = i
            results.append(result)
        
        # Pausa entre experimentos
        time.sleep(5)
    
    return results

def create_analysis_report(results):
    """Crear reporte de análisis con datos empíricos"""
    
    # Crear DataFrame para análisis
    data = []
    for result in results:
        row = {
            'experiment_id': result['experiment_id'],
            'cache_size': result['config']['cache_size'],
            'policy': result['config']['policy'],
            'distribution': result['config']['distribution'],
            'total_requests': result['metrics']['total_requests'],
            'hit_rate': result['metrics']['hit_rate'],
            'miss_rate': result['metrics']['miss_rate'],
            'throughput': result['metrics']['throughput'],
            'utilization': result['metrics']['cache_utilization'],
            'success_rate': result['metrics']['success_rate']
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Guardar datos
    df.to_csv('cache_analysis_results.csv', index=False)
    
    # Crear visualizaciones
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # 1. Hit Rate por tamaño de cache
    cache_size_analysis = df.groupby('cache_size')['hit_rate'].mean()
    axes[0,0].bar(cache_size_analysis.index, cache_size_analysis.values)
    axes[0,0].set_title('Hit Rate vs Tamaño de Cache')
    axes[0,0].set_xlabel('Tamaño de Cache')
    axes[0,0].set_ylabel('Hit Rate')
    
    # 2. Hit Rate por política
    policy_analysis = df.groupby('policy')['hit_rate'].mean()
    axes[0,1].bar(policy_analysis.index, policy_analysis.values, color='orange')
    axes[0,1].set_title('Hit Rate vs Política de Cache')
    axes[0,1].set_xlabel('Política')
    axes[0,1].set_ylabel('Hit Rate')
    
    # 3. Hit Rate por distribución
    dist_analysis = df.groupby('distribution')['hit_rate'].mean()
    axes[1,0].bar(dist_analysis.index, dist_analysis.values, color='green')
    axes[1,0].set_title('Hit Rate vs Distribución de Tráfico')
    axes[1,0].set_xlabel('Distribución')
    axes[1,0].set_ylabel('Hit Rate')
    axes[1,0].tick_params(axis='x', rotation=45)
    
    # 4. Throughput vs Cache Size
    axes[1,1].scatter(df['cache_size'], df['throughput'], c=df['hit_rate'], cmap='viridis')
    axes[1,1].set_title('Throughput vs Tamaño de Cache')
    axes[1,1].set_xlabel('Tamaño de Cache')
    axes[1,1].set_ylabel('Throughput (req/s)')
    
    plt.tight_layout()
    plt.savefig('cache_analysis_plots.png', dpi=300, bbox_inches='tight')
    
    # Generar tablas comparativas
    print("\n📊 TABLAS COMPARATIVAS:")
    print("\n1. ANÁLISIS POR TAMAÑO DE CACHE:")
    print(df.groupby('cache_size')[['hit_rate', 'miss_rate', 'throughput', 'utilization']].mean().round(3))
    
    print("\n2. ANÁLISIS POR POLÍTICA:")
    print(df.groupby('policy')[['hit_rate', 'miss_rate', 'throughput', 'utilization']].mean().round(3))
    
    print("\n3. ANÁLISIS POR DISTRIBUCIÓN DE TRÁFICO:")
    print(df.groupby('distribution')[['hit_rate', 'miss_rate', 'throughput', 'utilization']].mean().round(3))
    
    # Identificar mejores configuraciones
    print("\n4. MEJORES CONFIGURACIONES (Top 3 Hit Rate):")
    best_configs = df.nlargest(3, 'hit_rate')[['cache_size', 'policy', 'distribution', 'hit_rate', 'throughput']]
    print(best_configs)
    
    print("\n5. PEORES CONFIGURACIONES (Bottom 3 Hit Rate):")
    worst_configs = df.nsmallest(3, 'hit_rate')[['cache_size', 'policy', 'distribution', 'hit_rate', 'throughput']]
    print(worst_configs)
    
    return df

if __name__ == "__main__":
    print("🔬 ANÁLISIS EXPERIMENTAL DE CACHÉ - VERSIÓN SIMPLIFICADA")
    print("=" * 60)
    
    # Ejecutar análisis completo
    results = run_comprehensive_analysis()
    
    # Generar reporte
    if results:
        df = create_analysis_report(results)
        print(f"\n🎉 Análisis completado! {len(results)} experimentos ejecutados.")
        print("📁 Archivos generados:")
        print("  - cache_analysis_results.csv")
        print("  - cache_analysis_plots.png")
    else:
        print("❌ No se pudieron obtener resultados")
