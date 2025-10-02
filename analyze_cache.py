#!/usr/bin/env python3
"""
Script de análisis experimental para el comportamiento de la caché
Genera datos empíricos para diferentes configuraciones y distribuciones de tráfico
"""

import subprocess
import time
import json
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os

class CacheAnalyzer:
    def __init__(self):
        self.results = []
        self.base_url = "http://localhost"
        self.services = {
            'cache': 8002,
            'traffic': 8005,
            'storage': 8001
        }
        
    def wait_for_services(self):
        """Espera a que todos los servicios estén disponibles"""
        for service, port in self.services.items():
            while True:
                try:
                    response = requests.get(f"{self.base_url}:{port}/health", timeout=5)
                    if response.status_code == 200:
                        print(f"✅ {service.title()} Service disponible")
                        break
                except:
                    print(f"⏳ Esperando {service} service...")
                    time.sleep(2)
    
    def restart_cache_with_config(self, cache_size, policy, ttl):
        """Reinicia el servicio de cache con nueva configuración"""
        print(f"\n🔧 Configurando cache: Size={cache_size}, Policy={policy}, TTL={ttl}s")
        
        # Detener cache service
        subprocess.run([
            "docker-compose", "stop", "cache"
        ], cwd="/Users/sebastianzuniga/Documents/Sistemas Distribuidos/Tarea-1-Sistemas-distribuidos")
        
        # Limpiar Redis
        subprocess.run([
            "docker-compose", "exec", "-T", "redis", "redis-cli", "FLUSHALL"
        ], cwd="/Users/sebastianzuniga/Documents/Sistemas Distribuidos/Tarea-1-Sistemas-distribuidos")
        
        # Actualizar variables de entorno y reiniciar
        env_vars = [
            "CACHE_MAX_SIZE=" + str(cache_size),
            "CACHE_POLICY=" + policy,
            "CACHE_TTL=" + str(ttl)
        ]
        
        # Reiniciar con nueva configuración
        subprocess.run([
            "docker-compose", "up", "-d", "cache"
        ], cwd="/Users/sebastianzuniga/Documents/Sistemas Distribuidos/Tarea-1-Sistemas-distribuidos", 
        env=dict(os.environ, **dict(var.split('=') for var in env_vars)))
        
        time.sleep(10)  # Esperar que el servicio se estabilice
        
    def run_traffic_experiment(self, distribution, rate, duration):
        """Ejecuta un experimento de tráfico y recopila métricas"""
        print(f"🚀 Ejecutando tráfico: {distribution}, rate={rate}, duration={duration}s")
        
        # Obtener estado inicial
        initial_stats = self.get_cache_stats()
        start_time = time.time()
        
        # Iniciar tráfico
        traffic_config = {
            "distribution": distribution,
            "rate": rate,
            "duration": duration
        }
        
        response = requests.post(
            f"{self.base_url}:{self.services['traffic']}/start-traffic",
            json=traffic_config,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code != 200:
            print(f"❌ Error iniciando tráfico: {response.text}")
            return None
            
        # Monitorear durante la ejecución
        metrics_timeline = []
        while True:
            traffic_stats = self.get_traffic_stats()
            if not traffic_stats.get('is_running', True):
                break
                
            cache_stats = self.get_cache_stats()
            metrics_timeline.append({
                'timestamp': time.time() - start_time,
                'cache_size': len(self.get_redis_keys()),
                'requests_sent': traffic_stats.get('total_requests', 0)
            })
            
            time.sleep(2)
        
        # Obtener estadísticas finales
        final_stats = self.get_cache_stats()
        traffic_final = self.get_traffic_stats()
        
        return {
            'initial_stats': initial_stats,
            'final_stats': final_stats,
            'traffic_stats': traffic_final,
            'timeline': metrics_timeline
        }
    
    def get_cache_stats(self):
        """Obtiene estadísticas actuales del cache"""
        try:
            response = requests.get(f"{self.base_url}:{self.services['cache']}/cache/stats")
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return {}
    
    def get_traffic_stats(self):
        """Obtiene estadísticas del generador de tráfico"""
        try:
            response = requests.get(f"{self.base_url}:{self.services['traffic']}/stats")
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return {}
    
    def get_redis_keys(self):
        """Obtiene las keys actuales en Redis"""
        try:
            result = subprocess.run([
                "docker-compose", "exec", "-T", "redis", "redis-cli", "KEYS", "*"
            ], cwd="/Users/sebastianzuniga/Documents/Sistemas Distribuidos/Tarea-1-Sistemas-distribuidos",
            capture_output=True, text=True)
            
            keys = result.stdout.strip().split('\n') if result.stdout.strip() else []
            return [k for k in keys if k and k != '(empty list or set)']
        except:
            return []
    
    def run_comprehensive_analysis(self):
        """Ejecuta análisis completo con múltiples configuraciones"""
        
        # Configuraciones experimentales
        cache_configs = [
            {'size': 10, 'policy': 'lru', 'ttl': 300},   # Cache pequeño, TTL bajo
            {'size': 10, 'policy': 'lfu', 'ttl': 300},   # LFU pequeño
            {'size': 10, 'policy': 'fifo', 'ttl': 300},  # FIFO pequeño
            {'size': 50, 'policy': 'lru', 'ttl': 600},   # Cache mediano
            {'size': 100, 'policy': 'lru', 'ttl': 1200}, # Cache grande
        ]
        
        # Distribuciones de tráfico
        traffic_patterns = [
            {'distribution': 'uniform', 'rate': 3.0, 'duration': 60},
            {'distribution': 'poisson', 'rate': 3.0, 'duration': 60},
            {'distribution': 'exponential', 'rate': 3.0, 'duration': 60},
            {'distribution': 'normal', 'rate': 3.0, 'duration': 60},
            {'distribution': 'uniform', 'rate': 8.0, 'duration': 45},  # Alto stress
        ]
        
        print("📊 INICIANDO ANÁLISIS EXPERIMENTAL COMPLETO")
        print("=" * 60)
        
        experiment_id = 0
        
        for cache_config in cache_configs:
            for traffic_pattern in traffic_patterns:
                experiment_id += 1
                print(f"\n🧪 EXPERIMENTO {experiment_id}/{len(cache_configs) * len(traffic_patterns)}")
                print(f"Cache: {cache_config}")
                print(f"Traffic: {traffic_pattern}")
                
                # Configurar cache
                self.restart_cache_with_config(
                    cache_config['size'], 
                    cache_config['policy'], 
                    cache_config['ttl']
                )
                
                # Esperar servicios
                time.sleep(5)
                
                # Ejecutar experimento
                result = self.run_traffic_experiment(
                    traffic_pattern['distribution'],
                    traffic_pattern['rate'],
                    traffic_pattern['duration']
                )
                
                if result:
                    # Calcular métricas
                    traffic_stats = result['traffic_stats']
                    total_requests = traffic_stats.get('total_requests', 0)
                    successful_requests = traffic_stats.get('successful_requests', 0)
                    
                    # Estimar hits y misses basado en comportamiento observado
                    cache_keys_final = len(self.get_redis_keys())
                    estimated_misses = min(cache_keys_final, cache_config['size'])
                    estimated_hits = max(0, total_requests - estimated_misses)
                    
                    hit_rate = estimated_hits / total_requests if total_requests > 0 else 0
                    miss_rate = 1 - hit_rate
                    
                    experiment_result = {
                        'experiment_id': experiment_id,
                        'cache_size': cache_config['size'],
                        'cache_policy': cache_config['policy'],
                        'cache_ttl': cache_config['ttl'],
                        'traffic_distribution': traffic_pattern['distribution'],
                        'traffic_rate': traffic_pattern['rate'],
                        'traffic_duration': traffic_pattern['duration'],
                        'total_requests': total_requests,
                        'successful_requests': successful_requests,
                        'estimated_hits': estimated_hits,
                        'estimated_misses': estimated_misses,
                        'hit_rate': hit_rate,
                        'miss_rate': miss_rate,
                        'cache_utilization': cache_keys_final / cache_config['size'],
                        'throughput': successful_requests / traffic_pattern['duration'],
                        'success_rate': traffic_stats.get('success_rate', 0),
                        'actual_rate': traffic_stats.get('current_rate', 0),
                        'timeline': result['timeline']
                    }
                    
                    self.results.append(experiment_result)
                    
                    print(f"✅ Resultado: Hit Rate={hit_rate:.2%}, Throughput={experiment_result['throughput']:.2f} req/s")
                
                # Pausa entre experimentos
                time.sleep(10)
        
        return self.results
    
    def generate_analysis_report(self):
        """Genera reporte de análisis con gráficos y tablas"""
        if not self.results:
            print("❌ No hay resultados para analizar")
            return
            
        df = pd.DataFrame(self.results)
        
        # Crear directorio de resultados
        results_dir = "/Users/sebastianzuniga/Documents/Sistemas Distribuidos/Tarea-1-Sistemas-distribuidos/analysis_results"
        os.makedirs(results_dir, exist_ok=True)
        
        # Guardar datos raw
        df.to_csv(f"{results_dir}/cache_analysis_data.csv", index=False)
        
        # Generar gráficos
        self.create_visualizations(df, results_dir)
        
        # Generar tablas comparativas
        self.create_comparative_tables(df, results_dir)
        
        print(f"📊 Análisis completo guardado en: {results_dir}")
        
    def create_visualizations(self, df, results_dir):
        """Crea visualizaciones del análisis"""
        
        # Configurar estilo
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # 1. Hit Rate por Distribución de Tráfico
        plt.figure(figsize=(12, 8))
        
        plt.subplot(2, 2, 1)
        hit_by_distribution = df.groupby('traffic_distribution')['hit_rate'].mean()
        hit_by_distribution.plot(kind='bar')
        plt.title('Hit Rate Promedio por Distribución de Tráfico')
        plt.xlabel('Distribución')
        plt.ylabel('Hit Rate')
        plt.xticks(rotation=45)
        
        # 2. Hit Rate por Política de Cache
        plt.subplot(2, 2, 2)
        hit_by_policy = df.groupby('cache_policy')['hit_rate'].mean()
        hit_by_policy.plot(kind='bar', color='orange')
        plt.title('Hit Rate Promedio por Política de Cache')
        plt.xlabel('Política')
        plt.ylabel('Hit Rate')
        
        # 3. Throughput vs Cache Size
        plt.subplot(2, 2, 3)
        plt.scatter(df['cache_size'], df['throughput'], c=df['hit_rate'], cmap='viridis')
        plt.colorbar(label='Hit Rate')
        plt.xlabel('Tamaño de Cache')
        plt.ylabel('Throughput (req/s)')
        plt.title('Relación Tamaño de Cache vs Throughput')
        
        # 4. Miss Rate por Configuración
        plt.subplot(2, 2, 4)
        miss_data = df.pivot_table(values='miss_rate', index='cache_size', columns='cache_policy', aggfunc='mean')
        sns.heatmap(miss_data, annot=True, fmt='.2%', cmap='Reds')
        plt.title('Miss Rate por Configuración')
        
        plt.tight_layout()
        plt.savefig(f"{results_dir}/cache_analysis_plots.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # Gráfico adicional: Evolución temporal
        plt.figure(figsize=(15, 10))
        
        # Seleccionar algunos experimentos representativos
        selected_experiments = df[df['experiment_id'].isin([1, 5, 10, 15, 20])]
        
        for idx, row in selected_experiments.iterrows():
            if row['timeline']:
                timeline_df = pd.DataFrame(row['timeline'])
                plt.plot(timeline_df['timestamp'], timeline_df['cache_size'], 
                        label=f"Exp {row['experiment_id']}: {row['cache_policy']}({row['cache_size']}) - {row['traffic_distribution']}")
        
        plt.xlabel('Tiempo (s)')
        plt.ylabel('Elementos en Cache')
        plt.title('Evolución del Tamaño de Cache Durante Experimentos')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig(f"{results_dir}/cache_timeline_evolution.png", dpi=300, bbox_inches='tight')
        plt.close()
        
    def create_comparative_tables(self, df, results_dir):
        """Crea tablas comparativas detalladas"""
        
        # Tabla 1: Rendimiento por Distribución de Tráfico
        distribution_analysis = df.groupby('traffic_distribution').agg({
            'hit_rate': ['mean', 'std'],
            'miss_rate': ['mean', 'std'],
            'throughput': ['mean', 'std'],
            'cache_utilization': ['mean', 'std']
        }).round(4)
        
        distribution_analysis.to_csv(f"{results_dir}/distribution_analysis.csv")
        
        # Tabla 2: Rendimiento por Política de Cache
        policy_analysis = df.groupby('cache_policy').agg({
            'hit_rate': ['mean', 'std'],
            'miss_rate': ['mean', 'std'],
            'throughput': ['mean', 'std'],
            'cache_utilization': ['mean', 'std']
        }).round(4)
        
        policy_analysis.to_csv(f"{results_dir}/policy_analysis.csv")
        
        # Tabla 3: Impacto del Tamaño de Cache
        size_analysis = df.groupby('cache_size').agg({
            'hit_rate': ['mean', 'std'],
            'miss_rate': ['mean', 'std'],
            'throughput': ['mean', 'std'],
            'cache_utilization': ['mean', 'std']
        }).round(4)
        
        size_analysis.to_csv(f"{results_dir}/size_analysis.csv")
        
        # Tabla 4: Mejores y Peores Configuraciones
        best_hit_rate = df.nlargest(5, 'hit_rate')[['cache_size', 'cache_policy', 'traffic_distribution', 'hit_rate', 'throughput']]
        worst_hit_rate = df.nsmallest(5, 'hit_rate')[['cache_size', 'cache_policy', 'traffic_distribution', 'hit_rate', 'throughput']]
        
        best_hit_rate.to_csv(f"{results_dir}/best_configurations.csv", index=False)
        worst_hit_rate.to_csv(f"{results_dir}/worst_configurations.csv", index=False)
        
        print("📋 Tablas comparativas generadas:")
        print("  - distribution_analysis.csv: Análisis por distribución de tráfico")
        print("  - policy_analysis.csv: Análisis por política de cache")
        print("  - size_analysis.csv: Análisis por tamaño de cache")
        print("  - best_configurations.csv: Mejores configuraciones")
        print("  - worst_configurations.csv: Peores configuraciones")

if __name__ == "__main__":
    analyzer = CacheAnalyzer()
    
    print("🔬 ANÁLISIS EXPERIMENTAL DE CACHÉ")
    print("=" * 50)
    print("Este script ejecutará múltiples experimentos para analizar:")
    print("- Impacto de distribuciones de tráfico")
    print("- Efecto de políticas de cache (LRU, LFU, FIFO)")
    print("- Influencia del tamaño de cache")
    print("- Generación de datos empíricos y visualizaciones")
    print()
    
    # Verificar servicios
    analyzer.wait_for_services()
    
    # Ejecutar análisis completo
    results = analyzer.run_comprehensive_analysis()
    
    # Generar reporte
    analyzer.generate_analysis_report()
    
    print("🎉 Análisis experimental completado!")
