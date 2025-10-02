#!/usr/bin/env python3


import os
import time
import logging
import requests
from flask import Flask, jsonify, request
from typing import Dict, Optional
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class LLMManager:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY no configurada")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')

        self.score_url = os.getenv('SCORE_URL', 'http://score:8000')
        self.storage_url = os.getenv('STORAGE_URL', 'http://storage:8000')

        self.generation_config = {
            'temperature': 0.7,
            'top_p': 0.8,
            'top_k': 40,
            'max_output_tokens': 1024,
        }
        
        logger.info("LLM Service inicializado con Gemini Pro")

    def _create_prompt(self, question_data: Dict) -> str:
        
        title = question_data.get('title', '')
        question = question_data.get('question', '')
        
        prompt = f"""Como un experto asistente, responde de manera clara y útil a la siguiente pregunta.

Título: {title}
Pregunta: {question}

Proporciona una respuesta informativa, precisa y bien estructurada. La respuesta debe ser directa y helpful, similar a como respondería un humano experto en el tema."""

        return prompt

    def generate_response(self, question_data: Dict) -> Dict:
        
        start_time = time.time()
        
        try:

            prompt = self._create_prompt(question_data)

            print(f"🤖 Generando respuesta con Gemini para: '{question_data.get('title', 'Pregunta sin título')[:50]}...'")
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            if not response.text:
                print(f"❌ Gemini no pudo generar respuesta para pregunta {question_data.get('id')}")
                return {
                    "error": "No se pudo generar respuesta",
                    "question_id": question_data.get('id')
                }
            
            llm_response = response.text.strip()
            response_time_ms = int((time.time() - start_time) * 1000)
            
            print(f"✅ Respuesta generada en {response_time_ms}ms - Enviando a evaluación...")
            logger.info(f"Respuesta generada para pregunta {question_data.get('id')} en {response_time_ms}ms")

            response_data = {
                "question_id": question_data.get('id'),
                "question_title": question_data.get('title'),
                "question_text": question_data.get('question'),
                "original_answer": question_data.get('best_answer'),
                "llm_response": llm_response,
                "response_time_ms": response_time_ms,
                "llm_model": "gemini-pro"
            }

            try:
                score_response = requests.post(
                    f"{self.score_url}/evaluate-response",
                    json=response_data,
                    timeout=30
                )
                
                if score_response.status_code == 200:
                    score_data = score_response.json()
                    response_data.update(score_data)
                else:
                    logger.warning(f"Error en score service: {score_response.status_code}")
                    response_data["quality_score"] = None
                    response_data["score_error"] = "Error calculando score"
                    
            except Exception as e:
                logger.error(f"Error llamando score service: {e}")
                response_data["quality_score"] = None
                response_data["score_error"] = str(e)
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error generando respuesta: {e}")
            return {
                "error": f"Error en LLM: {str(e)}",
                "question_id": question_data.get('id'),
                "response_time_ms": int((time.time() - start_time) * 1000)
            }

    def get_model_info(self) -> Dict:
        
        try:
            return {
                "model": "gemini-pro",
                "provider": "Google",
                "status": "active",
                "config": self.generation_config
            }
        except Exception as e:
            return {"error": str(e)}

try:
    llm_manager = LLMManager()
except Exception as e:
    logger.error(f"Error inicializando LLM Manager: {e}")
    llm_manager = None

@app.route('/health', methods=['GET'])
def health_check():
    
    if llm_manager is None:
        return jsonify({"status": "unhealthy", "service": "llm", "error": "LLM not initialized"}), 500
    
    return jsonify({"status": "healthy", "service": "llm"})

@app.route('/generate-response', methods=['POST'])
def generate_response():
    
    if llm_manager is None:
        return jsonify({"error": "LLM service no disponible"}), 500
    
    question_data = request.get_json()
    
    if not question_data:
        return jsonify({"error": "No se proporcionaron datos de pregunta"}), 400
    
    required_fields = ['id', 'question']
    missing_fields = [field for field in required_fields if field not in question_data]
    if missing_fields:
        return jsonify({"error": f"Campos faltantes: {missing_fields}"}), 400
    
    result = llm_manager.generate_response(question_data)
    return jsonify(result)

@app.route('/model-info', methods=['GET'])
def get_model_info():
    
    if llm_manager is None:
        return jsonify({"error": "LLM service no disponible"}), 500
    
    info = llm_manager.get_model_info()
    return jsonify(info)

@app.route('/test-generation', methods=['POST'])
def test_generation():
    
    if llm_manager is None:
        return jsonify({"error": "LLM service no disponible"}), 500
    
    data = request.get_json()
    test_question = data.get('question', 'What is artificial intelligence?')
    
    test_data = {
        'id': 999,
        'title': 'Test Question',
        'question': test_question,
        'best_answer': 'This is a test answer'
    }
    
    result = llm_manager.generate_response(test_data)
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
