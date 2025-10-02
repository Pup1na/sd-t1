#!/usr/bin/env python3


import os
import sys
import csv
import time
import logging
import psycopg2
from psycopg2.extras import execute_values
from typing import List, Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataLoader:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'yahoo_answers'),
            'user': os.getenv('DB_USER', 'admin'),
            'password': os.getenv('DB_PASSWORD', 'password')
        }
        self.data_path = os.getenv('DATA_PATH', '/app/data')
        self.connection = None

    def connect_db(self, max_retries=10, delay=5):
        
        for attempt in range(max_retries):
            try:
                self.connection = psycopg2.connect(**self.db_config)
                logger.info("✅ Conectado a la base de datos")
                return True
            except psycopg2.OperationalError as e:
                logger.warning(f"⚠️  Intento {attempt + 1}/{max_retries} fallido: {e}")
                if attempt < max_retries - 1:
                    time.sleep(delay)
                else:
                    logger.error("❌ No se pudo conectar a la base de datos")
                    return False

    def check_data_exists(self) -> bool:
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM yahoo_questions WHERE yahoo_id NOT LIKE 'sample_%'")
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            logger.error(f"Error verificando datos existentes: {e}")
            return False

    def find_csv_files(self) -> List[str]:
        
        csv_files = []
        if not os.path.exists(self.data_path):
            logger.warning(f"Directorio de datos no existe: {self.data_path}")
            return csv_files

        for file in os.listdir(self.data_path):
            if file.endswith('.csv'):
                file_path = os.path.join(self.data_path, file)

                if os.path.getsize(file_path) > 1000:
                    csv_files.append(file_path)
        
        logger.info(f"Archivos CSV encontrados: {csv_files}")
        return csv_files

    def load_csv_to_db(self, csv_file: str, batch_size: int = 1000) -> int:
        
        logger.info(f"📊 Cargando datos desde: {csv_file}")
        
        try:

            import csv
            
            total_rows = 0
            valid_rows = 0

            with open(csv_file, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                total_rows = sum(1 for row in csv_reader)
            
            logger.info(f"Total de filas en CSV: {total_rows}")

            with open(csv_file, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                headers = csv_reader.fieldnames
                expected_columns = ['class', 'title', 'question', 'best_answer']
                
                if not all(col in headers for col in expected_columns):
                    logger.error(f"Columnas faltantes. Esperadas: {expected_columns}, Encontradas: {headers}")
                    return 0

            records_inserted = 0
            with self.connection.cursor() as cursor:
                with open(csv_file, 'r', encoding='utf-8') as file:
                    csv_reader = csv.DictReader(file)
                    
                    values = []
                    row_count = 0
                    
                    for row in csv_reader:
                        row_count += 1

                        if (row.get('title', '').strip() and 
                            row.get('question', '').strip() and 
                            row.get('best_answer', '').strip() and
                            row.get('class', '').strip()):
                            
                            yahoo_id = f"csv_{os.path.basename(csv_file)}_{row_count}"
                            
                            try:
                                class_id = int(row['class'])
                                values.append((
                                    yahoo_id,
                                    class_id,
                                    str(row['title'])[:500],
                                    str(row['question'])[:2000],
                                    str(row['best_answer'])[:2000]
                                ))
                                valid_rows += 1
                            except ValueError:
                                continue

                        if len(values) >= batch_size:
                            insert_query = """
                                INSERT INTO yahoo_questions (yahoo_id, class_id, title, question, best_answer)
                                VALUES %s
                                ON CONFLICT (yahoo_id) DO NOTHING
                            
                            INSERT INTO yahoo_questions (yahoo_id, class_id, title, question, best_answer)
                            VALUES %s
                            ON CONFLICT (yahoo_id) DO NOTHING
                        Inicializar estadísticas para las preguntas cargadas"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO question_stats (question_id, access_count, cache_hits)
                    SELECT id, 0, 0 FROM yahoo_questions
                    WHERE id NOT IN (SELECT question_id FROM question_stats WHERE question_id IS NOT NULL)
                Obtener estadísticas de la base de datos"""
        try:
            with self.connection.cursor() as cursor:
                stats = {}

                cursor.execute("SELECT COUNT(*) FROM yahoo_questions")
                stats['total_questions'] = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT class_id, COUNT(*) 
                    FROM yahoo_questions 
                    GROUP BY class_id 
                    ORDER BY class_id
                Ejecutar el proceso de carga de datos"""
        print("=" * 60)
        print("🚀 INICIANDO CARGA DE DATOS DE YAHOO ANSWERS")
        print("=" * 60)
        logger.info("🚀 Iniciando Data Loader para Yahoo Answers")

        print("📡 Conectando a la base de datos PostgreSQL...")
        if not self.connect_db():
            print("❌ Error: No se pudo conectar a la base de datos")
            sys.exit(1)
        print("✅ Conexión a base de datos establecida")

        try:

            print("🔍 Verificando si ya existen datos en la base de datos...")
            if self.check_data_exists():
                print("ℹ️  Ya existen datos reales en la base de datos")
                stats = self.get_database_stats()
                print(f"📊 Estadísticas actuales:")
                for key, value in stats.items():
                    print(f"   {key}: {value}")
                print("✅ CARGA DE DATOS COMPLETADA (datos ya existían)")
                return

            print("📁 Buscando archivos CSV para cargar...")
            csv_files = self.find_csv_files()
            
            if not csv_files:
                print("⚠️  No se encontraron archivos CSV grandes para cargar")
                print("ℹ️  Usando datos de ejemplo ya incluidos en la base de datos")
                print("💡 Para cargar datos reales, ejecuta: ./download_data.sh")
            else:
                print(f"📦 Encontrados {len(csv_files)} archivos CSV para procesar")

                total_loaded = 0
                for i, csv_file in enumerate(csv_files, 1):
                    print(f"📊 Procesando archivo {i}/{len(csv_files)}: {csv_file}")
                    loaded = self.load_csv_to_db(csv_file)
                    total_loaded += loaded
                    print(f"✅ Archivo {i} completado: {loaded} registros cargados")

                print("=" * 50)
                print(f"🎉 CARGA COMPLETADA: {total_loaded} registros totales")
                print("=" * 50)

            self.initialize_stats()

            print("📊 Estadísticas finales de la base de datos:")
            stats = self.get_database_stats()
            for key, value in stats.items():
                print(f"   📈 {key}: {value}")

            print("=" * 60)
            print("🎉 ¡CARGA DE DATOS COMPLETADA EXITOSAMENTE!")
            print("✅ Base de datos lista para recibir consultas")
            print("=" * 60)

        except Exception as e:
            logger.error(f"Error en el proceso de carga: {e}")
            sys.exit(1)
        finally:
            if self.connection:
                self.connection.close()

if __name__ == "__main__":
    loader = DataLoader()
    loader.run()
