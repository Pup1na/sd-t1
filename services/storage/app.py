#!/usr/bin/env python3

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request
from typing import Dict, List, Optional, Any
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class DatabaseManager:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'yahoo_answers'),
            'user': os.getenv('DB_USER', 'admin'),
            'password': os.getenv('DB_PASSWORD', 'password')
        }

    def get_connection(self):
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)

    def get_random_question(self) -> Optional[Dict]:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, yahoo_id, class_id, title, question, best_answer
                        FROM yahoo_questions 
                        ORDER BY RANDOM() 
                        LIMIT 1
                    Obtener pregunta por ID"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, yahoo_id, class_id, title, question, best_answer
                        FROM yahoo_questions 
                        WHERE id = %s
                    Incrementar contador de acceso a pregunta"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    if is_cache_hit:
                        cursor.execute("""
                            UPDATE question_stats 
                            SET access_count = access_count + 1,
                                cache_hits = cache_hits + 1,
                                last_accessed = CURRENT_TIMESTAMP
                            WHERE question_id = %s
                        
                            UPDATE question_stats 
                            SET access_count = access_count + 1,
                                last_accessed = CURRENT_TIMESTAMP
                            WHERE question_id = %s
                        
                            INSERT INTO question_stats (question_id, access_count, cache_hits)
                            VALUES (%s, 1, %s)
                        Guardar respuesta del LLM"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO llm_responses (question_id, llm_response, quality_score, 
                                                 response_time_ms, llm_model)
                        VALUES (%s, %s, %s, %s, %s)
                    Obtener estadísticas de la base de datos"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    stats = {}

                    cursor.execute("SELECT COUNT(*) FROM yahoo_questions")
                    stats['total_questions'] = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(*) FROM llm_responses")
                    stats['total_llm_responses'] = cursor.fetchone()[0]

                    cursor.execute("""
                        SELECT 
                            SUM(access_count) as total_accesses,
                            SUM(cache_hits) as total_cache_hits,
                            AVG(access_count) as avg_accesses_per_question
                        FROM question_stats
                    Health check endpoint"""
    return jsonify({"status": "healthy", "service": "storage"})

@app.route('/question/random', methods=['GET'])
def get_random_question():
    
    question = db_manager.get_random_question()
    if question:
        return jsonify(question)
    else:
        return jsonify({"error": "No se pudo obtener pregunta"}), 500

@app.route('/question/<int:question_id>', methods=['GET'])
def get_question(question_id):
    
    question = db_manager.get_question_by_id(question_id)
    if question:
        return jsonify(question)
    else:
        return jsonify({"error": "Pregunta no encontrada"}), 404

@app.route('/question/<int:question_id>/access', methods=['POST'])
def increment_access(question_id):
    
    data = request.get_json() or {}
    is_cache_hit = data.get('cache_hit', False)
    
    db_manager.increment_access_count(question_id, is_cache_hit)
    return jsonify({"success": True})

@app.route('/llm-response', methods=['POST'])
def save_response():
    
    data = request.get_json()
    
    required_fields = ['question_id', 'llm_response']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Faltan campos requeridos"}), 400
    
    success = db_manager.save_llm_response(
        question_id=data['question_id'],
        llm_response=data['llm_response'],
        quality_score=data.get('quality_score'),
        response_time_ms=data.get('response_time_ms'),
        llm_model=data.get('llm_model', 'gemini')
    )
    
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Error guardando respuesta"}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    
    stats = db_manager.get_database_stats()
    return jsonify(stats)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
