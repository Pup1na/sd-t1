#!/usr/bin/env python3


import os
import time
import random
import logging
import requests
import threading
from flask import Flask, jsonify, request
from typing import Dict, List, Optional
import numpy as np
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class DistributionType(Enum):
    POISSON = "poisson"
    UNIFORM = "uniform"
    EXPONENTIAL = "exponential"
    NORMAL = "normal"

class TrafficGenerator:
    def __init__(self):

        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'yahoo_answers'),
            'user': os.getenv('DB_USER', 'admin'),
            'password': os.getenv('DB_PASSWORD', 'password')
        }

        self.cache_url = os.getenv('CACHE_URL', 'http://cache:8000')
        self.storage_url = os.getenv('STORAGE_URL', 'http://storage:8000')

        self.is_running = False
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.start_time = None
        self.thread_pool = ThreadPoolExecutor(max_workers=10)

        self.question_ids = []
        self.last_refresh = 0
        self.refresh_interval = 300
        
        logger.info("Traffic Generator inicializado")

    def get_db_connection(self):
        
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)

    def refresh_question_ids(self):
        
        try:
            current_time = time.time()
            if current_time - self.last_refresh < self.refresh_interval:
                return
            
            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM yahoo_questions ORDER BY id")
                    results = cursor.fetchall()
                    self.question_ids = [row['id'] for row in results]
                    self.last_refresh = current_time
                    
            logger.info(f"Cache de IDs actualizado: {len(self.question_ids)} preguntas disponibles")
            
        except Exception as e:
            logger.error(f"Error actualizando cache de IDs: {e}")

    def get_random_question_id(self) -> Optional[int]:
        
        self.refresh_question_ids()
        
        if not self.question_ids:
            return None
        
        return random.choice(self.question_ids)

    def get_weighted_question_id(self, weights: Dict[int, float] = None) -> Optional[int]:
        
        self.refresh_question_ids()
        
        if not self.question_ids:
            return None
        
        if weights:

            weighted_ids = []
            weighted_probs = []
            for qid in self.question_ids:
                if qid in weights:
                    weighted_ids.append(qid)
                    weighted_probs.append(weights[qid])
            
            if weighted_ids:
                return np.random.choice(weighted_ids, p=np.array(weighted_probs)/sum(weighted_probs))
        
        return random.choice(self.question_ids)

    def generate_arrival_times(self, distribution: DistributionType, rate: float, duration: float) -> List[float]:
        
        arrival_times = []
        current_time = 0
        
        if distribution == DistributionType.POISSON:

            while current_time < duration:
                interval = np.random.exponential(1.0 / rate)
                current_time += interval
                if current_time < duration:
                    arrival_times.append(current_time)
                    
        elif distribution == DistributionType.UNIFORM:

            interval = 1.0 / rate
            current_time = interval
            while current_time < duration:
                arrival_times.append(current_time)
                current_time += interval
                
        elif distribution == DistributionType.EXPONENTIAL:

            while current_time < duration:
                interval = np.random.exponential(1.0 / rate)
                current_time += interval
                if current_time < duration:
                    arrival_times.append(current_time)
                    
        elif distribution == DistributionType.NORMAL:

            while current_time < duration:
                interval = max(0.1, np.random.normal(1.0 / rate, 0.2 / rate))
                current_time += interval
                if current_time < duration:
                    arrival_times.append(current_time)
        
        return arrival_times

    def send_request(self, question_id: int) -> Dict:
        
        start_time = time.time()
        
        try:
            response = requests.get(
                f"{self.cache_url}/question/{question_id}",
                timeout=30
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                result = response.json()
                result['request_time_ms'] = int(response_time)
                self.successful_requests += 1
                return result
            else:
                self.failed_requests += 1
                return {
                    'error': f'HTTP {response.status_code}',
                    'question_id': question_id,
                    'request_time_ms': int(response_time)
                }
                
        except Exception as e:
            self.failed_requests += 1
            return {
                'error': str(e),
                'question_id': question_id,
                'request_time_ms': int((time.time() - start_time) * 1000)
            }

    def run_traffic_pattern(self, config: Dict) -> Dict:
        
        distribution = DistributionType(config.get('distribution', 'poisson'))
        rate = config.get('rate', 1.0)
        duration = config.get('duration', 60)
        
        print(f"\n🚦 INICIANDO GENERACIÓN DE TRÁFICO")
        print(f"   📊 Distribución: {distribution.value}")
        print(f"   ⚡ Rate: {rate} consultas/segundo") 
        print(f"   ⏱️  Duración: {duration} segundos")
        logger.info(f"Iniciando patrón de tráfico: {distribution.value}, rate={rate}/s, duration={duration}s")

        arrival_times = self.generate_arrival_times(distribution, rate, duration)
        
        print(f"   🎯 Total de solicitudes programadas: {len(arrival_times)}")
        logger.info(f"Generadas {len(arrival_times)} solicitudes")
        
        self.is_running = True
        self.start_time = time.time()
        self.total_requests = len(arrival_times)
        self.successful_requests = 0
        self.failed_requests = 0

        for i, arrival_time in enumerate(arrival_times):
            if not self.is_running:
                break

            elapsed = time.time() - self.start_time
            wait_time = arrival_time - elapsed
            if wait_time > 0:
                time.sleep(wait_time)

            question_id = self.get_random_question_id()
            if question_id is None:
                logger.warning("No hay preguntas disponibles")
                continue

            self.thread_pool.submit(self.send_request, question_id)

            if (i + 1) % 10 == 0:
                elapsed_time = time.time() - self.start_time
                current_rate = (i + 1) / elapsed_time if elapsed_time > 0 else 0
                print(f"📈 Progreso: {i + 1}/{len(arrival_times)} solicitudes enviadas (Rate actual: {current_rate:.2f}/s)")
                logger.info(f"Enviadas {i + 1}/{len(arrival_times)} solicitudes")

        time.sleep(5)
        self.is_running = False
        
        total_time = time.time() - self.start_time
        
        result = {
            'pattern': distribution.value,
            'configured_rate': rate,
            'duration': duration,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.successful_requests / self.total_requests if self.total_requests > 0 else 0,
            'actual_rate': self.total_requests / total_time if total_time > 0 else 0,
            'total_time': total_time
        }
        
        print(f"\n🏁 TRÁFICO COMPLETADO:")
        print(f"   ✅ Solicitudes exitosas: {self.successful_requests}")
        print(f"   ❌ Solicitudes fallidas: {self.failed_requests}")
        print(f"   📊 Tasa de éxito: {result['success_rate']*100:.1f}%")
        print(f"   ⚡ Rate real: {result['actual_rate']:.2f} consultas/s")
        print(f"   ⏱️  Tiempo total: {total_time:.1f}s")
        
        logger.info(f"Patrón completado: {result}")
        return result

    def get_stats(self) -> Dict:
        
        if self.start_time:
            elapsed = time.time() - self.start_time
            current_rate = self.total_requests / elapsed if elapsed > 0 else 0
        else:
            elapsed = 0
            current_rate = 0
        
        return {
            'is_running': self.is_running,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.successful_requests / self.total_requests if self.total_requests > 0 else 0,
            'elapsed_time': elapsed,
            'current_rate': current_rate,
            'available_questions': len(self.question_ids)
        }

traffic_generator = TrafficGenerator()

@app.route('/health', methods=['GET'])
def health_check():
    
    return jsonify({"status": "healthy", "service": "traffic_generator"})

@app.route('/start-traffic', methods=['POST'])
def start_traffic():
    
    if traffic_generator.is_running:
        return jsonify({"error": "Traffic generator ya está ejecutándose"}), 400
    
    config = request.get_json() or {}

    distribution = config.get('distribution', 'poisson')
    if distribution not in [d.value for d in DistributionType]:
        return jsonify({"error": f"Distribución inválida: {distribution}"}), 400

    def run_async():
        traffic_generator.run_traffic_pattern(config)
    
    threading.Thread(target=run_async, daemon=True).start()
    
    return jsonify({"success": True, "message": "Traffic generation started", "config": config})

@app.route('/stop-traffic', methods=['POST'])
def stop_traffic():
    
    traffic_generator.is_running = False
    return jsonify({"success": True, "message": "Traffic generation stopped"})

@app.route('/stats', methods=['GET'])
def get_stats():
    
    stats = traffic_generator.get_stats()
    return jsonify(stats)

@app.route('/test-request', methods=['POST'])
def test_request():
    
    data = request.get_json() or {}
    question_id = data.get('question_id')
    
    if not question_id:
        question_id = traffic_generator.get_random_question_id()
        if not question_id:
            return jsonify({"error": "No hay preguntas disponibles"}), 400
    
    result = traffic_generator.send_request(question_id)
    return jsonify(result)

@app.route('/patterns', methods=['GET'])
def get_patterns():
    
    patterns = [
        {
            "name": "Light Load",
            "description": "Carga ligera con llegadas uniformes",
            "config": {"distribution": "uniform", "rate": 0.5, "duration": 120}
        },
        {
            "name": "Normal Load",
            "description": "Carga normal con proceso de Poisson",
            "config": {"distribution": "poisson", "rate": 2.0, "duration": 300}
        },
        {
            "name": "Burst Load",
            "description": "Ráfagas de tráfico",
            "config": {"distribution": "exponential", "rate": 5.0, "duration": 180}
        },
        {
            "name": "Steady Load",
            "description": "Carga constante",
            "config": {"distribution": "normal", "rate": 1.0, "duration": 600}
        }
    ]
    return jsonify(patterns)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
