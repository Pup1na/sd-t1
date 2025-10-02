#!/usr/bin/env python3


import os
import time
import logging
import requests
import numpy as np
from flask import Flask, jsonify, request
from typing import Dict, List, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from nltk.tokenize import word_tokenize
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class ScoreManager:
    def __init__(self):
        self.storage_url = os.getenv('STORAGE_URL', 'http://storage:8000')

        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')

        self.tfidf_vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=1000,
            ngram_range=(1, 2),
            lowercase=True
        )
        
        logger.info("Score Service inicializado")

    def preprocess_text(self, text: str) -> str:
        
        if not text:
            return ""

        text = text.lower()

        text = re.sub(r'[^\w\s\.\,\!\?]', ' ', text)

        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def calculate_cosine_similarity(self, text1: str, text2: str) -> float:
        
        try:

            clean_text1 = self.preprocess_text(text1)
            clean_text2 = self.preprocess_text(text2)
            
            if not clean_text1 or not clean_text2:
                return 0.0

            vectors = self.tfidf_vectorizer.fit_transform([clean_text1, clean_text2])

            similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculando similitud coseno: {e}")
            return 0.0

    def calculate_bleu_score(self, reference: str, candidate: str) -> float:
        
        try:

            reference_tokens = word_tokenize(self.preprocess_text(reference))
            candidate_tokens = word_tokenize(self.preprocess_text(candidate))
            
            if not reference_tokens or not candidate_tokens:
                return 0.0

            smoothing = SmoothingFunction().method1
            bleu = sentence_bleu(
                [reference_tokens], 
                candidate_tokens,
                smoothing_function=smoothing,
                weights=(0.25, 0.25, 0.25, 0.25)
            )
            
            return float(bleu)
            
        except Exception as e:
            logger.error(f"Error calculando BLEU score: {e}")
            return 0.0

    def calculate_length_similarity(self, text1: str, text2: str) -> float:
        
        try:
            len1 = len(text1.split())
            len2 = len(text2.split())
            
            if len1 == 0 and len2 == 0:
                return 1.0
            if len1 == 0 or len2 == 0:
                return 0.0

            ratio = min(len1, len2) / max(len1, len2)
            return float(ratio)
            
        except Exception as e:
            logger.error(f"Error calculando similitud de longitud: {e}")
            return 0.0

    def calculate_keyword_overlap(self, text1: str, text2: str) -> float:
        
        try:

            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being'}
            
            words1 = set(word.lower() for word in text1.split() if word.lower() not in stop_words and len(word) > 2)
            words2 = set(word.lower() for word in text2.split() if word.lower() not in stop_words and len(word) > 2)
            
            if not words1 and not words2:
                return 1.0
            if not words1 or not words2:
                return 0.0

            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            return float(intersection / union) if union > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculando keyword overlap: {e}")
            return 0.0

    def calculate_composite_score(self, original_answer: str, llm_response: str) -> Dict:
        
        try:

            cosine_sim = self.calculate_cosine_similarity(original_answer, llm_response)
            bleu_score = self.calculate_bleu_score(original_answer, llm_response)
            length_sim = self.calculate_length_similarity(original_answer, llm_response)
            keyword_overlap = self.calculate_keyword_overlap(original_answer, llm_response)

            weights = {
                'cosine': 0.4,
                'bleu': 0.3,
                'length': 0.1,
                'keyword': 0.2
            }

            composite_score = (
                cosine_sim * weights['cosine'] +
                bleu_score * weights['bleu'] +
                length_sim * weights['length'] +
                keyword_overlap * weights['keyword']
            )
            
            return {
                'composite_score': round(float(composite_score), 4),
                'cosine_similarity': round(float(cosine_sim), 4),
                'bleu_score': round(float(bleu_score), 4),
                'length_similarity': round(float(length_sim), 4),
                'keyword_overlap': round(float(keyword_overlap), 4),
                'weights': weights
            }
            
        except Exception as e:
            logger.error(f"Error calculando score compuesto: {e}")
            return {
                'composite_score': 0.0,
                'error': str(e)
            }

    def evaluate_response(self, response_data: Dict) -> Dict:
        
        start_time = time.time()
        
        try:

            question_id = response_data.get('question_id')
            original_answer = response_data.get('original_answer', '')
            llm_response = response_data.get('llm_response', '')
            
            if not original_answer or not llm_response:
                return {'error': 'Respuestas faltantes para evaluación'}

            scores = self.calculate_composite_score(original_answer, llm_response)

            scores['question_id'] = question_id
            scores['evaluation_time_ms'] = int((time.time() - start_time) * 1000)
            scores['original_length'] = len(original_answer.split())
            scores['llm_length'] = len(llm_response.split())

            try:
                storage_data = {
                    'question_id': question_id,
                    'llm_response': llm_response,
                    'quality_score': scores['composite_score'],
                    'response_time_ms': response_data.get('response_time_ms'),
                    'llm_model': response_data.get('llm_model', 'unknown')
                }
                
                storage_response = requests.post(
                    f"{self.storage_url}/llm-response",
                    json=storage_data,
                    timeout=10
                )
                
                if storage_response.status_code == 200:
                    scores['stored'] = True
                else:
                    scores['stored'] = False
                    scores['storage_error'] = f"HTTP {storage_response.status_code}"
                    
            except Exception as e:
                logger.error(f"Error guardando en storage: {e}")
                scores['stored'] = False
                scores['storage_error'] = str(e)

            score_value = scores['composite_score']
            if score_value >= 0.7:
                print(f"🏆 EXCELENTE RESPUESTA - Pregunta {question_id}: Score = {score_value:.4f}")
                print(f"   📈 Métricas: Cosine={scores.get('cosine_similarity', 0):.3f}, BLEU={scores.get('bleu_score', 0):.3f}")
            elif score_value >= 0.5:
                print(f"👍 BUENA RESPUESTA - Pregunta {question_id}: Score = {score_value:.4f}")
            else:
                print(f"📊 Respuesta evaluada - Pregunta {question_id}: Score = {score_value:.4f}")
            
            logger.info(f"Respuesta evaluada para pregunta {question_id}: score={scores['composite_score']}")
            return scores
            
        except Exception as e:
            logger.error(f"Error evaluando respuesta: {e}")
            return {
                'error': str(e),
                'question_id': response_data.get('question_id'),
                'evaluation_time_ms': int((time.time() - start_time) * 1000)
            }

    def get_evaluation_stats(self) -> Dict:
        
        try:

            storage_response = requests.get(f"{self.storage_url}/stats")
            if storage_response.status_code == 200:
                storage_stats = storage_response.json()
            else:
                storage_stats = {}
            
            return {
                'service': 'score',
                'metrics_used': ['cosine_similarity', 'bleu_score', 'length_similarity', 'keyword_overlap'],
                'composite_weights': {
                    'cosine': 0.4,
                    'bleu': 0.3,
                    'length': 0.1,
                    'keyword': 0.2
                },
                'storage_stats': storage_stats
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {'error': str(e)}

score_manager = ScoreManager()

@app.route('/health', methods=['GET'])
def health_check():
    
    return jsonify({"status": "healthy", "service": "score"})

@app.route('/evaluate-response', methods=['POST'])
def evaluate_response():
    
    response_data = request.get_json()
    
    if not response_data:
        return jsonify({"error": "No se proporcionaron datos"}), 400
    
    required_fields = ['question_id', 'original_answer', 'llm_response']
    missing_fields = [field for field in required_fields if field not in response_data]
    if missing_fields:
        return jsonify({"error": f"Campos faltantes: {missing_fields}"}), 400
    
    result = score_manager.evaluate_response(response_data)
    return jsonify(result)

@app.route('/test-score', methods=['POST'])
def test_score():
    
    data = request.get_json()
    
    text1 = data.get('text1', 'This is a sample answer about artificial intelligence.')
    text2 = data.get('text2', 'AI is a technology that simulates human intelligence.')
    
    scores = score_manager.calculate_composite_score(text1, text2)
    return jsonify(scores)

@app.route('/stats', methods=['GET'])
def get_stats():
    
    stats = score_manager.get_evaluation_stats()
    return jsonify(stats)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
