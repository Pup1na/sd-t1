#!/usr/bin/env python3


import os
import json
import time
import logging
import redis
import requests
from flask import Flask, jsonify, request
from typing import Dict, Optional, Any
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class CachePolicy(Enum):
    LRU = "lru"
    LFU = "lfu" 
    FIFO = "fifo"

class CacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=0,
            decode_responses=True
        )
        self.storage_url = os.getenv('STORAGE_URL', 'http://storage:8000')
        self.llm_url = os.getenv('LLM_URL', 'http://llm:8000')

        self.cache_ttl = int(os.getenv('CACHE_TTL', 3600))
        self.max_cache_size = int(os.getenv('MAX_CACHE_SIZE', 1000))
        self.cache_policy = CachePolicy(os.getenv('CACHE_POLICY', 'lru'))

        self._init_stats_counters()
        
        logger.info(f"Cache configurado: TTL={self.cache_ttl}s, Max={self.max_cache_size}, Policy={self.cache_policy.value}")

    def _init_stats_counters(self):
        
        if not self.redis_client.exists("stats:cache_hits"):
            self.redis_client.set("stats:cache_hits", 0)
        if not self.redis_client.exists("stats:cache_misses"):
            self.redis_client.set("stats:cache_misses", 0)
        if not self.redis_client.exists("stats:total_requests"):
            self.redis_client.set("stats:total_requests", 0)

    def _generate_cache_key(self, question_id: int) -> str:
        
        return f"question:{question_id}"

    def _update_access_metadata(self, cache_key: str):
        
        if self.cache_policy == CachePolicy.LRU:

            self.redis_client.zadd("cache:lru", {cache_key: time.time()})
        elif self.cache_policy == CachePolicy.LFU:

            self.redis_client.zincrby("cache:lfu", 1, cache_key)

    def _enforce_cache_limit(self):
        
        current_size = self.redis_client.dbsize()
        
        if current_size <= self.max_cache_size:
            return

        to_remove = current_size - self.max_cache_size + 10
        
        if self.cache_policy == CachePolicy.LRU:

            old_keys = self.redis_client.zrange("cache:lru", 0, to_remove - 1)
            for key in old_keys:
                self.redis_client.delete(key)
                self.redis_client.zrem("cache:lru", key)
                logger.debug(f"Removido por LRU: {key}")
                
        elif self.cache_policy == CachePolicy.LFU:

            old_keys = self.redis_client.zrange("cache:lfu", 0, to_remove - 1)
            for key in old_keys:
                self.redis_client.delete(key)
                self.redis_client.zrem("cache:lfu", key)
                logger.debug(f"Removido por LFU: {key}")
                
        elif self.cache_policy == CachePolicy.FIFO:

            old_keys = self.redis_client.zrange("cache:fifo", 0, to_remove - 1)
            for key in old_keys:
                self.redis_client.delete(key)
                self.redis_client.zrem("cache:fifo", key)
                logger.debug(f"Removido por FIFO: {key}")

    def get_cached_response(self, question_id: int) -> Optional[Dict]:
        
        cache_key = self._generate_cache_key(question_id)
        
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                self._update_access_metadata(cache_key)
                print(f"🎯 CACHE HIT - Pregunta {question_id} encontrada en cache")
                logger.info(f"Cache HIT para pregunta {question_id}")
                return json.loads(cached_data)
            else:
                print(f"💾 CACHE MISS - Pregunta {question_id} no está en cache, procesando...")
                logger.info(f"Cache MISS para pregunta {question_id}")
                return None
        except Exception as e:
            logger.error(f"Error accediendo cache: {e}")
            return None

    def store_response(self, question_id: int, response_data: Dict):
        
        cache_key = self._generate_cache_key(question_id)
        
        try:

            self.redis_client.setex(
                cache_key, 
                self.cache_ttl, 
                json.dumps(response_data)
            )

            current_time = time.time()
            if self.cache_policy == CachePolicy.LRU:
                self.redis_client.zadd("cache:lru", {cache_key: current_time})
            elif self.cache_policy == CachePolicy.LFU:
                self.redis_client.zadd("cache:lfu", {cache_key: 1})
            elif self.cache_policy == CachePolicy.FIFO:
                self.redis_client.zadd("cache:fifo", {cache_key: current_time})

            self._enforce_cache_limit()
            
            print(f"💾 Respuesta almacenada en cache para pregunta {question_id} (TTL: {self.cache_ttl}s)")
            logger.info(f"Respuesta almacenada en cache para pregunta {question_id}")
            
        except Exception as e:
            logger.error(f"Error almacenando en cache: {e}")

    def get_cache_stats(self) -> Dict:
        
        try:

            cache_hits = int(self.redis_client.get("stats:cache_hits") or 0)
            cache_misses = int(self.redis_client.get("stats:cache_misses") or 0)
            total_requests = int(self.redis_client.get("stats:total_requests") or 0)

            hit_rate = cache_hits / total_requests if total_requests > 0 else 0
            miss_rate = cache_misses / total_requests if total_requests > 0 else 0
            
            current_cache_size = len([k for k in self.redis_client.keys("question:*")])
            
            stats = {
                'total_keys': self.redis_client.dbsize(),
                'policy': self.cache_policy.value,
                'ttl': self.cache_ttl,
                'max_size': self.max_cache_size,
                'cache_hits': cache_hits,
                'cache_misses': cache_misses,
                'total_requests': total_requests,
                'hit_rate': round(hit_rate, 4),
                'miss_rate': round(miss_rate, 4),
                'current_size': current_cache_size,
                'utilization': round(current_cache_size / self.max_cache_size, 4) if self.max_cache_size > 0 else 0
            }

            if self.cache_policy == CachePolicy.LRU:
                stats['lru_entries'] = self.redis_client.zcard("cache:lru")
            elif self.cache_policy == CachePolicy.LFU:
                stats['lfu_entries'] = self.redis_client.zcard("cache:lfu")
            elif self.cache_policy == CachePolicy.FIFO:
                stats['fifo_entries'] = self.redis_client.zcard("cache:fifo")
                
            return stats
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}

    def process_question_request(self, question_id: int) -> Dict:
        
        start_time = time.time()
        print(f"\n🔄 PROCESANDO CONSULTA - Pregunta ID: {question_id}")

        self.redis_client.incr("stats:total_requests")

        cached_response = self.get_cached_response(question_id)
        if cached_response:

            self.redis_client.incr("stats:cache_hits")

            try:
                requests.post(f"{self.storage_url}/question/{question_id}/access",
                            json={"cache_hit": True})
            except Exception as e:
                logger.warning(f"Error actualizando stats de cache hit: {e}")
            
            cached_response['cache_hit'] = True
            cached_response['response_time_ms'] = int((time.time() - start_time) * 1000)
            return cached_response

        try:
            question_response = requests.get(f"{self.storage_url}/question/{question_id}")
            if question_response.status_code != 200:
                return {"error": "Pregunta no encontrada", "question_id": question_id}
            
            question_data = question_response.json()
        except Exception as e:
            logger.error(f"Error obteniendo pregunta {question_id}: {e}")
            return {"error": "Error obteniendo pregunta"}

        print(f"🤖 Enviando pregunta al LLM Service para generar respuesta...")
        try:
            llm_response = requests.post(f"{self.llm_url}/generate-response", 
                                       json=question_data)
            if llm_response.status_code != 200:
                print(f"❌ Error en LLM Service: HTTP {llm_response.status_code}")
                return {"error": "Error generando respuesta LLM"}
            
            response_data = llm_response.json()
            print(f"✅ Respuesta generada por LLM y evaluada")
        except Exception as e:
            print(f"❌ Error llamando LLM service: {e}")
            logger.error(f"Error llamando LLM service: {e}")
            return {"error": "Error en servicio LLM"}

        self.redis_client.incr("stats:cache_misses")

        self.store_response(question_id, response_data)

        try:
            requests.post(f"{self.storage_url}/question/{question_id}/access",
                        json={"cache_hit": False})
        except Exception as e:
            logger.warning(f"Error actualizando stats de cache miss: {e}")

        response_data['cache_hit'] = False
        response_data['response_time_ms'] = int((time.time() - start_time) * 1000)
        return response_data

cache_manager = CacheManager()

@app.route('/health', methods=['GET'])
def health_check():
    
    try:
        cache_manager.redis_client.ping()
        return jsonify({"status": "healthy", "service": "cache"})
    except:
        return jsonify({"status": "unhealthy", "service": "cache"}), 500

@app.route('/question/<int:question_id>', methods=['GET'])
def process_question(question_id):
    
    result = cache_manager.process_question_request(question_id)
    return jsonify(result)

@app.route('/cache/stats', methods=['GET'])
def get_cache_stats():
    
    stats = cache_manager.get_cache_stats()
    return jsonify(stats)

@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    
    try:
        cache_manager.redis_client.flushdb()
        return jsonify({"success": True, "message": "Cache limpiado"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cache/policy', methods=['POST'])
def change_cache_policy():
    
    data = request.get_json()
    policy = data.get('policy')
    
    if policy not in [p.value for p in CachePolicy]:
        return jsonify({"error": "Política inválida"}), 400
    
    cache_manager.cache_policy = CachePolicy(policy)
    return jsonify({"success": True, "new_policy": policy})

@app.route('/cache/reset-stats', methods=['POST'])
def reset_cache_stats():
    
    try:
        cache_manager.redis_client.set("stats:cache_hits", 0)
        cache_manager.redis_client.set("stats:cache_misses", 0)
        cache_manager.redis_client.set("stats:total_requests", 0)
        return jsonify({"success": True, "message": "Estadísticas reseteadas"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
